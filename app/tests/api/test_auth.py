from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import jwt
import pytest
from app.core.config import settings
from sqlalchemy import select, delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.core.security import verify_password, JWTManager, TokenType

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


from app.models.accounts import (
    UserModel as User,
    UserModel,
    ActivationTokenModel,
    PasswordResetTokenModel,
    UserGroupModel,
    UserGroupEnum,
    RefreshTokenModel,
)
from app.tests.conftest import db_session

REGISTER_URL = "/api/accounts/register/"

pytestmark = pytest.mark.anyio


def registration_payload(
    email: str = "user@example.com",
    password: str = "Password1!",
) -> dict[str, str]:
    return {
        "email": email,
        "password": password,
    }


async def test_successful_registration(
    client: AsyncClient, db_session: AsyncSession, fake_email_sender
):
    payload = registration_payload()
    response = await client.post(
        REGISTER_URL,
        json=payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["email"] == "user@example.com"

    user = await db_session.scalar(select(User).where(User.id == data["id"]))

    assert not user.is_active

    activation_email = next(
        email
        for email in fake_email_sender.sent_emails
        if email["type"] == "activation"
    )

    activation_token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )

    assert activation_token is not None

    assert activation_email["email"] == payload["email"]
    assert activation_email["link"] == (
        f"{settings.FRONTEND_URL}/activate" f"?token={activation_token.token}"
    )


async def test_invalid_email_returns_422(
    client: AsyncClient,
):
    response = await client.post(
        REGISTER_URL,
        json=registration_payload(
            email="invalid-email",
        ),
    )

    assert response.status_code == 422


async def test_short_password_returns_422(
    client: AsyncClient,
):
    response = await client.post(
        REGISTER_URL,
        json=registration_payload(
            password="Pass1!",
        ),
    )

    assert response.status_code == 422


async def test_duplicate_email_returns_409(
    client: AsyncClient,
):
    payload = registration_payload(
        email="duplicate@example.com",
    )

    first_response = await client.post(
        REGISTER_URL,
        json=payload,
    )

    second_response = await client.post(
        REGISTER_URL,
        json=payload,
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": f"A user with this email {payload["email"]} already exists.",
    }


async def test_email_is_normalized(
    client: AsyncClient,
):
    response = await client.post(
        REGISTER_URL,
        json=registration_payload(
            email="user@EXAMPLE.COM",
        ),
    )

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"


async def test_password_is_stored_hashed(
    client: AsyncClient,
    db_session: AsyncSession,
):
    plain_password = "Password1!"

    response = await client.post(
        REGISTER_URL,
        json=registration_payload(
            email="hashed@example.com",
            password=plain_password,
        ),
    )

    assert response.status_code == 201

    user = await db_session.scalar(
        select(User).where(User.email == "hashed@example.com")
    )

    assert user is not None
    assert user._hashed_password != plain_password

    assert verify_password(
        plain_password,
        user._hashed_password,
    )


async def test_password_hash_is_absent_from_response(
    client: AsyncClient,
):
    response = await client.post(
        REGISTER_URL,
        json=registration_payload(
            email="safe-response@example.com",
        ),
    )

    assert response.status_code == 201

    data = response.json()

    assert "password" not in data
    assert "hashed_password" not in data
    assert "_hashed_password" not in data


ACTIVATION_URL = "/api/accounts/activate/"


async def test_activate_account_success(
    client: AsyncClient, db_session: AsyncSession, fake_email_sender
):
    """
    Test successful activation of a user account.

    Steps:
    - Register a new user.
    - Verify the user is inactive.
    - Activate the user using the activation token.
    - Verify the user is activated and the token is deleted.
    """

    user_data = registration_payload()

    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel)
        .options(joinedload(UserModel.activation_token))
        .where(UserModel.email == user_data["email"])
    )
    assert user is not None
    assert not user.is_active

    assert user.activation_token is not None and user.activation_token.token is not None

    activation_payload = {
        "email": user_data["email"],
        "token": user.activation_token.token,
    }

    activation_response = await client.post(ACTIVATION_URL, json=activation_payload)
    assert activation_response.status_code == 200
    assert (
        activation_response.json()["message"] == "User account activated successfully."
    )

    user = await db_session.scalar(
        select(UserModel)
        .options(joinedload(UserModel.activation_token))
        .where(UserModel.email == user_data["email"])
    )
    await db_session.refresh(user)
    assert user.is_active

    token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )
    assert token is None

    activation_complete_email = next(
        email
        for email in fake_email_sender.sent_emails
        if email["type"] == "activation_complete"
    )

    assert activation_complete_email["email"] == user_data["email"]
    assert activation_complete_email["link"] == f"{settings.FRONTEND_URL}/login"


async def test_activate_user_with_expired_token(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test activation with an expired token.

    Ensures that the endpoint returns a 400 error when the activation token is expired.
    Steps:
    - Register a new user.
    - Retrieve the user and their activation token.
    - Manually set the token's expiration to a past date.
    - Attempt to activate the account with the expired token.
    - Verify that the response is a 400 error with the expected error message.
    """
    user_data = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert user is not None
    assert not user.is_active

    activation_token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )

    assert activation_token is not None

    activation_token.expires_at = datetime.now(timezone.utc) - timedelta(days=2)
    await db_session.commit()

    activation_payload = {
        "email": user_data["email"],
        "token": activation_token.token,
    }
    activation_response = await client.post(ACTIVATION_URL, json=activation_payload)

    assert activation_response.status_code == 400
    assert (
        activation_response.json()["detail"] == "Invalid or expired activation token."
    )


async def test_activate_user_with_deleted_token(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test activation with a deleted token.

    Ensures that the endpoint returns a 400 error when the activation token has been deleted.

    Steps:
    - Register a new user.
    - Verify that the user is created and inactive.
    - Delete the activation token from the database.
    - Attempt to activate the account using the deleted token.
    - Verify that a 400 error is returned with the appropriate error message.
    """
    user_data = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert user is not None
    assert not user.is_active

    activation_token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )

    assert activation_token is not None

    token_value = activation_token.token

    await db_session.execute(
        delete(ActivationTokenModel).where(
            ActivationTokenModel.id == activation_token.id
        )
    )
    await db_session.commit()

    activation_payload = {"email": user_data["email"], "token": token_value}
    activation_response = await client.post(ACTIVATION_URL, json=activation_payload)
    assert activation_response.status_code == 400
    assert (
        activation_response.json()["detail"] == "Invalid or expired activation token."
    )


async def test_activate_already_active_user(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test activation of an already active user.

    Ensures that the endpoint returns a 400 error if the user is already active.
    Steps:
    - Register a new user.
    - Mark the user as active in the database.
    - Attempt to activate the user using the activation token.
    - Verify that a 400 error with the expected error message is returned.
    """
    user_data = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert user is not None

    user.is_active = True
    await db_session.commit()

    activation_token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )

    assert activation_token is not None

    activation_payload = {
        "email": user_data["email"],
        "token": activation_token.token,
    }
    activation_response = await client.post(ACTIVATION_URL, json=activation_payload)
    assert activation_response.status_code == 400
    assert activation_response.json()["detail"] == "User account is already active."


REQUEST_RESET_TOKEN_URL = "/api/accounts/password-reset/request/"


async def test_request_password_reset_token_success(
    client: AsyncClient, db_session: AsyncSession, fake_email_sender
):
    """
    Test successful password reset token request.

    Ensures that a password reset token is created for an active user.

    Steps:
    - Register a new user.
    - Mark the user as active.
    - Request a password reset token.
    - Verify that the endpoint returns status 200 and the expected success message.
    - Query the database to confirm that a PasswordResetTokenModel record was created.
    - Verify that the token's expiration date is in the future.
    """
    user_data = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert user is not None

    user.is_active = True
    await db_session.commit()

    reset_payload = {"email": user_data["email"]}
    reset_response = await client.post(REQUEST_RESET_TOKEN_URL, json=reset_payload)
    assert reset_response.status_code == 200
    assert (
        reset_response.json()["message"]
        == "If you are registered, you will receive an email with instructions."
    )

    reset_token = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )
    assert reset_token is not None

    password_reset_email = next(
        email
        for email in fake_email_sender.sent_emails
        if email["type"] == "password_reset"
    )

    assert password_reset_email["email"] == user_data["email"]
    assert password_reset_email["link"] == (
        f"{settings.FRONTEND_URL}/reset-password" f"?token={reset_token.token}"
    )

    assert reset_token.expires_at.tzinfo is not None
    assert reset_token.expires_at > datetime.now(timezone.utc)


async def test_request_password_reset_token_nonexistent_user(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test password reset token request for a non-existent user.

    Ensures that the endpoint responds with a generic success message and that no password reset token is created
    when the email does not exist in the database.
    """
    reset_payload = {"email": "nonexistent@example.com"}

    reset_response = await client.post(REQUEST_RESET_TOKEN_URL, json=reset_payload)
    assert reset_response.status_code == 200
    assert (
        reset_response.json()["message"]
        == "If you are registered, you will receive an email with instructions."
    )

    reset_token_count = await db_session.scalar(
        select(func.count(PasswordResetTokenModel.id))
    )
    assert reset_token_count == 0


async def test_request_password_reset_token_for_inactive_user(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test password reset token request for a registered but inactive user.

    Ensures that the endpoint returns the generic success message and that no password reset token
    is created when the user is registered but inactive.
    """
    user_data = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    created_user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert created_user is not None
    assert not created_user.is_active

    reset_payload = {"email": user_data["email"]}
    reset_response = await client.post(REQUEST_RESET_TOKEN_URL, json=reset_payload)
    assert reset_response.status_code == 200
    assert (
        reset_response.json()["message"]
        == "If you are registered, you will receive an email with instructions."
    )

    reset_token_count = await db_session.scalar(
        select(func.count(PasswordResetTokenModel.id))
    )
    assert reset_token_count == 0


RESET_TOKEN_COMPLETE_URL = "/api/accounts/password-reset/complete/"


async def test_reset_password_success(
    client: AsyncClient, db_session: AsyncSession, fake_email_sender
):
    """
    Test the complete password reset flow.

    Steps:
    - Register a user.
    - Activate the user.
    - Request a password reset token.
    - Use the token to reset the password.
    - Verify the password is updated in the database.
    """
    user_data = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    created_user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert created_user is not None

    activation_token = await db_session.scalar(
        select(ActivationTokenModel).where(
            ActivationTokenModel.user_id == created_user.id
        )
    )
    assert activation_token is not None

    activation_payload = {
        "email": user_data["email"],
        "token": activation_token.token,
    }

    activation_response = await client.post(ACTIVATION_URL, json=activation_payload)
    assert activation_response.status_code == 200

    await db_session.refresh(created_user)
    assert created_user.is_active

    reset_request_payload = {"email": user_data["email"]}

    reset_request_response = await client.post(
        REQUEST_RESET_TOKEN_URL, json=reset_request_payload
    )
    assert reset_request_response.status_code == 200

    reset_token_record = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == created_user.id
        )
    )
    assert reset_token_record is not None

    new_password = "NewSecurePassword123!"
    reset_payload = {
        "email": user_data["email"],
        "token": reset_token_record.token,
        "password": new_password,
    }
    reset_response = await client.post(RESET_TOKEN_COMPLETE_URL, json=reset_payload)
    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Password reset successfully."

    await db_session.refresh(created_user)
    assert created_user.verify_password(new_password)

    password_reset_complete_email = next(
        email
        for email in fake_email_sender.sent_emails
        if email["type"] == "password_reset_complete"
    )

    assert password_reset_complete_email["email"] == user_data["email"]
    assert password_reset_complete_email["link"] == (f"{settings.FRONTEND_URL}/login")


async def test_reset_password_invalid_email(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test password reset with an email that does not exist in the database.

    Validates that the endpoint returns a 400 status code and appropriate error message.
    """
    reset_payload = {
        "email": "nonexistent@example.com",
        "token": "random_token",
        "password": "NewSecurePassword123!",
    }

    response = await client.post(RESET_TOKEN_COMPLETE_URL, json=reset_payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email or token."


async def test_reset_password_invalid_token(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test password reset with an incorrect token.

    Validates that the endpoint returns a 400 status code and an appropriate error message when an invalid token is provided.
    Also ensures that any invalid token is removed from the database.
    """
    user_data = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert user is not None

    user.is_active = True
    await db_session.commit()

    reset_request_payload = {"email": user_data["email"]}
    response = await client.post(REQUEST_RESET_TOKEN_URL, json=reset_request_payload)
    assert response.status_code == 200

    reset_complete_payload = {
        "email": user_data["email"],
        "token": "incorrect_token",
        "password": "NewSecurePassword123!",
    }
    response = await client.post(RESET_TOKEN_COMPLETE_URL, json=reset_complete_payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email or token."

    token_record = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )
    assert token_record is None, "Invalid token was not removed."


async def test_reset_password_expired_token(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test password reset with an expired token.

    Validates that the endpoint returns a 400 status code and an appropriate error message when the password
    reset token is expired, and verifies that the expired token is removed from the database.
    """
    user_data = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert user is not None

    user.is_active = True
    await db_session.commit()

    reset_request_payload = {"email": user_data["email"]}
    response = await client.post(REQUEST_RESET_TOKEN_URL, json=reset_request_payload)
    assert response.status_code == 200

    token_record = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )
    assert token_record is not None

    token_record.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.commit()

    reset_complete_payload = {
        "email": user_data["email"],
        "token": token_record.token,
        "password": "NewSecurePassword123!",
    }
    reset_response = await client.post(
        RESET_TOKEN_COMPLETE_URL, json=reset_complete_payload
    )
    assert reset_response.status_code == 400
    assert reset_response.json()["detail"] == "Invalid email or token."

    expired_token = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )
    assert expired_token is None


async def test_reset_password_sqlalchemy_error(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test password reset when a database commit raises SQLAlchemyError.

    Validates that the endpoint returns a 500 Internal Server Error and the appropriate error message
    when an error occurs during the password reset process.

    Steps:
    - Register a new user.
    - Mark the user as active.
    - Request a password reset token.
    - Attempt to reset the password while simulating a database commit error.
    - Verify that a 500 error is returned with the expected error message.
    """
    user_data = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }
    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert user is not None

    user.is_active = True
    await db_session.commit()

    reset_request_payload = {"email": user_data["email"]}
    response = await client.post(REQUEST_RESET_TOKEN_URL, json=reset_request_payload)
    assert response.status_code == 200

    token_record = await db_session.scalar(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )
    assert token_record is not None

    reset_complete_payload = {
        "email": user_data["email"],
        "token": token_record.token,
        "password": "NewSecurePassword123!",
    }

    with patch(
        "app.repositories.accounts.AsyncSession.commit", side_effect=SQLAlchemyError
    ):
        reset_response = await client.post(
            RESET_TOKEN_COMPLETE_URL, json=reset_complete_payload
        )

    assert reset_response.status_code == 500
    assert (
        reset_response.json()["detail"]
        == "An error occurred while resetting the password."
    )


LOGIN_URL = "/api/accounts/login/"


async def test_login_user_success(client: AsyncClient, db_session: AsyncSession):
    """
    Test successful login.

    Validates that access and refresh tokens are returned, the refresh token is stored in the database,
    and both tokens are valid.
    """
    user_payload = {"email": "testuser@example.com", "password": "StrongPassword123!"}

    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    assert user_group is not None

    user = UserModel.create(
        email=user_payload["email"],
        raw_password=user_payload["password"],
        group_id=user_group.id,
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": user_payload["email"],
        "password": user_payload["password"],
    }
    response = await client.post(LOGIN_URL, json=login_payload)
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert "refresh_token" in response_data
    assert response_data["access_token"]
    assert response_data["refresh_token"]

    access_token_data = JWTManager.decode_access_token(response_data["access_token"])
    assert access_token_data["sub"] == str(user.id)

    refresh_token_data = JWTManager.decode_refresh_token(response_data["refresh_token"])
    assert refresh_token_data["sub"] == str(user.id)

    refresh_token_record = await db_session.scalar(
        select(RefreshTokenModel).where(RefreshTokenModel.user_id == user.id)
    )
    assert refresh_token_record is not None
    assert refresh_token_record.token == response_data["refresh_token"]

    assert refresh_token_record.expires_at.tzinfo is not None
    assert refresh_token_record.expires_at > datetime.now(timezone.utc)


async def test_login_user_invalid_cases(client: AsyncClient, db_session: AsyncSession):
    """
    Test login with invalid cases:
    1. Non-existent user.
    2. Incorrect password for an existing user.
    """
    login_payload = {"email": "nonexistent@example.com", "password": "SomePassword123!"}
    response = await client.post(LOGIN_URL, json=login_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."

    user_payload = {"email": "testuser@example.com", "password": "CorrectPassword123!"}
    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    assert user_group is not None

    user = UserModel.create(
        email=user_payload["email"],
        raw_password=user_payload["password"],
        group_id=user_group.id,
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload_incorrect_password = {
        "email": user_payload["email"],
        "password": "WrongPassword123!",
    }
    response = await client.post(LOGIN_URL, json=login_payload_incorrect_password)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


async def test_login_user_inactive_account(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test login with an inactive user account.

    Validates that the endpoint returns a 403 status code and an appropriate error message
    when attempting to log in with a user whose account is not activated.
    """
    user_payload = {
        "email": "inactiveuser@example.com",
        "password": "StrongPassword123!",
    }

    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    assert user_group is not None

    user = UserModel.create(
        email=user_payload["email"],
        raw_password=user_payload["password"],
        group_id=user_group.id,
    )
    user.is_active = False
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": user_payload["email"],
        "password": user_payload["password"],
    }
    response = await client.post(LOGIN_URL, json=login_payload)

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is not activated."


async def test_login_user_commit_error(client: AsyncClient, db_session: AsyncSession):
    """
    Test login when a database commit error occurs.

    Validates that the endpoint returns a 500 status code and an appropriate error message.
    """
    user_payload = {"email": "testuser@example.com", "password": "StrongPassword123!"}
    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    assert user_group is not None

    user = UserModel.create(
        email=user_payload["email"],
        raw_password=user_payload["password"],
        group_id=user_group.id,
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": user_payload["email"],
        "password": user_payload["password"],
    }

    with patch(
        "app.repositories.accounts.AsyncSession.commit", side_effect=SQLAlchemyError
    ):
        response = await client.post(LOGIN_URL, json=login_payload)

    assert response.status_code == 500
    assert (
        response.json()["detail"] == "An error occurred while processing the request."
    )


REFRESH_ACCESS_TOKEN_URL = "/api/accounts/refresh/"


def create_expired_test_refresh_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "type": TokenType.REFRESH,
        "iat": now,
        "exp": now - timedelta(days=1),
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )


async def test_refresh_access_token_success(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Test successful access token refresh.

    Validates that a new access token is returned when a valid refresh token is provided.
    Steps:
    - Create an active user in the database.
    - Log in the user to obtain a refresh token.
    - Use the refresh token to obtain a new access token.
    - Verify that the new access token contains the correct user ID.
    """
    user_payload = {"email": "testuser@example.com", "password": "StrongPassword123!"}
    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    assert user_group is not None

    user = UserModel.create(
        email=user_payload["email"],
        raw_password=user_payload["password"],
        group_id=user_group.id,
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": user_payload["email"],
        "password": user_payload["password"],
    }
    login_response = await client.post(LOGIN_URL, json=login_payload)
    assert login_response.status_code == 200

    login_data = login_response.json()
    refresh_token = login_data["refresh_token"]

    refresh_payload = {"refresh_token": refresh_token}
    refresh_response = await client.post(REFRESH_ACCESS_TOKEN_URL, json=refresh_payload)
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert "access_token" in refresh_data
    assert refresh_data["access_token"]

    access_token_data = JWTManager.decode_access_token(refresh_data["access_token"])
    assert access_token_data["sub"] == str(user.id)


async def test_refresh_access_token_expired_token(client: AsyncClient):
    """
    Test refresh token with expired token.

    Validates that a 400 status code and "Refresh token has expired." message are returned
    when the refresh token is expired.
    """
    expired_token = create_expired_test_refresh_token(user_id=1)

    refresh_payload = {"refresh_token": expired_token}
    refresh_response = await client.post(REFRESH_ACCESS_TOKEN_URL, json=refresh_payload)

    assert refresh_response.status_code == 400
    assert refresh_response.json()["detail"] == "Refresh token has expired."


async def test_refresh_access_token_token_not_found(client: AsyncClient):
    """
    Test refresh token when token is not found in the database.

    Validates that a 401 status code and 'Refresh token not found.' message
    are returned when the refresh token is not stored in the database.
    """
    refresh_token = JWTManager.create_refresh_token(user_id=1)
    refresh_payload = {"refresh_token": refresh_token}
    refresh_response = await client.post(REFRESH_ACCESS_TOKEN_URL, json=refresh_payload)

    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Refresh token not found."


async def test_refresh_access_token_user_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
):
    user_payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }

    user_group = await db_session.scalar(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    assert user_group is not None

    user = UserModel.create(
        email=user_payload["email"],
        raw_password=user_payload["password"],
        group_id=user_group.id,
    )
    user.is_active = True

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    invalid_user_id = 9999

    refresh_token = JWTManager.create_refresh_token(user_id=invalid_user_id)

    refresh_token_record = RefreshTokenModel.create(
        user_id=user.id,
        days_valid=7,
        token=refresh_token,
    )

    db_session.add(refresh_token_record)
    await db_session.commit()

    response = await client.post(
        REFRESH_ACCESS_TOKEN_URL,
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


RESEND_ACTIVATION_URL = "/api/accounts/activate/resend/"


async def test_resend_activation_without_existing_token_success(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_email_sender,
):
    user_data = {
        "email": "resend-no-token@example.com",
        "password": "StrongPassword123!",
    }

    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert user is not None
    assert not user.is_active

    activation_token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )
    assert activation_token is not None

    await db_session.delete(activation_token)
    await db_session.commit()

    activation_token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )
    assert activation_token is None

    emails_before_resend = len(fake_email_sender.sent_emails)

    response = await client.post(
        RESEND_ACTIVATION_URL,
        json={"email": user_data["email"]},
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "If the account exists and is not activated, "
        "an activation email will be sent."
    )

    new_token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )
    assert new_token is not None

    assert len(fake_email_sender.sent_emails) == emails_before_resend + 1

    resend_email = fake_email_sender.sent_emails[-1]

    assert resend_email["type"] == "activation"
    assert resend_email["email"] == user_data["email"]
    assert resend_email["link"] == (
        f"{settings.FRONTEND_URL}/activate" f"?token={new_token.token}"
    )


async def test_resend_activation_replaces_existing_token(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_email_sender,
):
    user_data = {
        "email": "resend-existing-token@example.com",
        "password": "StrongPassword123!",
    }

    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert user is not None
    assert not user.is_active

    old_token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )
    assert old_token is not None

    old_token_id = old_token.id
    old_token_value = old_token.token

    emails_before_resend = len(fake_email_sender.sent_emails)

    response = await client.post(
        RESEND_ACTIVATION_URL,
        json={"email": user_data["email"]},
    )

    assert response.status_code == 200

    tokens = (
        await db_session.scalars(
            select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
        )
    ).all()

    assert len(tokens) == 1

    new_token = tokens[0]

    assert new_token.id != old_token_id
    assert new_token.token != old_token_value

    assert len(fake_email_sender.sent_emails) == emails_before_resend + 1

    resend_email = fake_email_sender.sent_emails[-1]

    assert resend_email["type"] == "activation"
    assert resend_email["email"] == user_data["email"]
    assert resend_email["link"] == (
        f"{settings.FRONTEND_URL}/activate" f"?token={new_token.token}"
    )


async def test_resend_activation_for_active_user_does_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_email_sender,
):
    user_data = {
        "email": "active-resend@example.com",
        "password": "StrongPassword123!",
    }

    response = await client.post(
        REGISTER_URL,
        json=user_data,
    )
    assert response.status_code == 201

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == user_data["email"])
    )
    assert user is not None

    activation_token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )
    assert activation_token is not None

    activation_response = await client.post(
        ACTIVATION_URL,
        json={
            "email": user_data["email"],
            "token": activation_token.token,
        },
    )
    assert activation_response.status_code == 200

    await db_session.refresh(user)
    assert user.is_active

    emails_before_resend = len(fake_email_sender.sent_emails)

    response = await client.post(
        RESEND_ACTIVATION_URL,
        json={"email": user_data["email"]},
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "If the account exists and is not activated, "
        "an activation email will be sent."
    )

    token = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )

    assert token is None
    assert len(fake_email_sender.sent_emails) == emails_before_resend


async def test_resend_activation_for_unknown_email_does_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_email_sender,
):
    emails_before_resend = len(fake_email_sender.sent_emails)

    response = await client.post(
        RESEND_ACTIVATION_URL,
        json={"email": "unknown@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "If the account exists and is not activated, "
        "an activation email will be sent."
    )

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == "unknown@example.com")
    )
    assert user is None

    assert len(fake_email_sender.sent_emails) == emails_before_resend
