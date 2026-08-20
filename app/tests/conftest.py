import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_email_sender, get_s3_storage
from app.main import app
from app.database import Base, get_db
from app.models.accounts import UserGroupEnum, UserGroupModel
from app.notifications.interfaces import EmailSenderInterface

from app.tests.database import (
    TestSessionLocal,
    get_test_db,
    test_engine,
)

from app.storages import S3StorageInterface


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


class FakeEmailSender(EmailSenderInterface):
    def __init__(self):
        self.sent_emails = []

    async def send_activation_email(
        self,
        email: str,
        activation_link: str,
    ) -> None:
        self.sent_emails.append(
            {
                "type": "activation",
                "email": email,
                "link": activation_link,
            }
        )

    async def send_activation_complete_email(
        self,
        email: str,
        login_link: str,
    ) -> None:
        self.sent_emails.append(
            {
                "type": "activation_complete",
                "email": email,
                "link": login_link,
            }
        )

    async def send_password_reset_email(
        self,
        email: str,
        reset_link: str,
    ) -> None:
        self.sent_emails.append(
            {
                "type": "password_reset",
                "email": email,
                "link": reset_link,
            }
        )

    async def send_password_reset_complete_email(
        self,
        email: str,
        login_link: str,
    ) -> None:
        self.sent_emails.append(
            {
                "type": "password_reset_complete",
                "email": email,
                "link": login_link,
            }
        )


@pytest.fixture
def fake_email_sender():
    return FakeEmailSender()


class FakeS3Storage(S3StorageInterface):

    def __init__(self):
        self.files: dict[str, bytes] = {}

    async def upload_file(
        self,
        file_name: str,
        file_data: bytes,
        content_type: str,
    ) -> None:
        self.files[file_name] = file_data

    async def get_file_url(
        self,
        file_name: str,
    ) -> str:
        return f"http://test-storage/{file_name}"

    async def delete_file(
        self,
        file_name: str,
    ) -> None:
        self.files.pop(file_name, None)


@pytest.fixture
def fake_s3_storage():
    return FakeS3Storage()


@pytest.fixture
async def client(
    prepare_test_database,
    fake_email_sender,
):
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_email_sender] = lambda: fake_email_sender
    app.dependency_overrides[get_s3_storage] = lambda: fake_s3_storage

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()
