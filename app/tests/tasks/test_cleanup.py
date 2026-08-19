from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounts import ActivationTokenModel, UserModel
from app.tasks.cleanup import delete_expired_activation_tokens
from app.tests.database import TestSyncSessionLocal
from app.tests.api.test_auth import REGISTER_URL


async def test_delete_expired_activation_tokens(
    client: AsyncClient,
    db_session: AsyncSession,
):
    expired_user_data = {
        "email": "expired@example.com",
        "password": "StrongPassword123!",
    }
    valid_user_data = {
        "email": "valid@example.com",
        "password": "StrongPassword123!",
    }

    expired_response = await client.post(
        REGISTER_URL,
        json=expired_user_data,
    )
    valid_response = await client.post(
        REGISTER_URL,
        json=valid_user_data,
    )

    assert expired_response.status_code == 201
    assert valid_response.status_code == 201

    expired_token = await db_session.scalar(
        select(ActivationTokenModel)
        .join(UserModel)
        .where(UserModel.email == expired_user_data["email"])
    )
    valid_token = await db_session.scalar(
        select(ActivationTokenModel)
        .join(UserModel)
        .where(UserModel.email == valid_user_data["email"])
    )

    assert expired_token is not None
    assert valid_token is not None

    expired_token_id = expired_token.id
    valid_token_id = valid_token.id

    expired_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    valid_token.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    await db_session.commit()

    with TestSyncSessionLocal() as sync_db:
        deleted_count = delete_expired_activation_tokens(sync_db)

    assert deleted_count == 1

    expired_token_db = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.id == expired_token_id)
    )
    valid_token_db = await db_session.scalar(
        select(ActivationTokenModel).where(ActivationTokenModel.id == valid_token_id)
    )

    assert expired_token_db is None
    assert valid_token_db is not None
