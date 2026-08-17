import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import Base, get_db
from app.models.accounts import UserGroupEnum, UserGroupModel

from app.tests.database import (
    TestSessionLocal,
    get_test_db,
    test_engine,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def prepare_test_database(anyio_backend):
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        session.add_all(
            [
                UserGroupModel(name=UserGroupEnum.USER),
                UserGroupModel(name=UserGroupEnum.MODERATOR),
                UserGroupModel(name=UserGroupEnum.ADMIN),
            ]
        )
        await session.commit()

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(prepare_test_database):
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(prepare_test_database):
    app.dependency_overrides[get_db] = get_test_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()
