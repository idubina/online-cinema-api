from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select, delete, func
from sqlalchemy.orm import joinedload

from app.core.security import verify_password


from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


from app.models.accounts import (
    UserModel as User,
    UserModel,
    ActivationTokenModel,
    PasswordResetTokenModel,
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


async def test_successful_registration(client: AsyncClient, db_session: AsyncSession):
    response = await client.post(
        REGISTER_URL,
        json=registration_payload(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["email"] == "user@example.com"

    user = await db_session.scalar(select(User).where(User.id == data["id"]))

    assert not user.is_active


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


async def test_activate_account_success(client: AsyncClient, db_session: AsyncSession):
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
    client: AsyncClient, db_session: AsyncSession
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
