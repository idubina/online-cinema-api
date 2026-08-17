import pytest
from sqlalchemy import select


from app.core.security import verify_password


from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


from app.models.accounts import UserModel as User

REGISTER_URL = "/api/register/"

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
    client: AsyncClient,
):
    response = await client.post(
        REGISTER_URL,
        json=registration_payload(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["email"] == "user@example.com"


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
