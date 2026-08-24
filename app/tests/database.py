from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

test_engine = create_async_engine(
    settings.async_sqlalchemy_database_test_url,
    poolclass=NullPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_test_db():
    async with TestSessionLocal() as session:
        yield session


SYNC_TEST_DATABASE_URL = settings.async_sqlalchemy_database_test_url.replace(
    "postgresql+asyncpg",
    "postgresql+psycopg",
)

test_sync_engine = create_engine(
    SYNC_TEST_DATABASE_URL,
)

TestSyncSessionLocal = sessionmaker(
    bind=test_sync_engine,
    expire_on_commit=False,
)
