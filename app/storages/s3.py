import aioboto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    HTTPClientError,
    NoCredentialsError,
)

from app.exceptions import (
    S3ConnectionError,
    S3FileUploadError,
)
from app.storages.interfaces import S3StorageInterface


class S3StorageClient(S3StorageInterface):

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        public_url: str | None = None,
    ):
        self._endpoint_url = endpoint_url.rstrip("/")
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket_name = bucket_name

        self._public_url = public_url.rstrip("/") if public_url else self._endpoint_url

        self._session = aioboto3.Session(
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )

    async def upload_file(
        self,
        file_name: str,
        file_data: bytes,
        content_type: str,
    ) -> None:
        try:
            async with self._session.client(
                "s3",
                endpoint_url=self._endpoint_url,
            ) as client:
                await client.put_object(
                    Bucket=self._bucket_name,
                    Key=file_name,
                    Body=file_data,
                    ContentType=content_type,
                )

        except (
            HTTPClientError,
            NoCredentialsError,
        ) as error:
            raise S3ConnectionError(
                f"Failed to connect to S3 storage: {error}"
            ) from error

        except (BotoCoreError, ClientError) as error:
            raise S3FileUploadError(
                f"Failed to upload file to S3 storage: {error}"
            ) from error

    async def get_file_url(
        self,
        file_name: str,
    ) -> str:
        return f"{self._public_url}/" f"{self._bucket_name}/" f"{file_name}"

    async def delete_file(
        self,
        file_name: str,
    ) -> None:
        try:
            async with self._session.client(
                "s3",
                endpoint_url=self._endpoint_url,
            ) as client:
                await client.delete_object(
                    Bucket=self._bucket_name,
                    Key=file_name,
                )

        except (
            HTTPClientError,
            NoCredentialsError,
        ) as error:
            raise S3ConnectionError(
                f"Failed to connect to S3 storage: {error}"
            ) from error

        except (BotoCoreError, ClientError) as error:
            raise S3FileUploadError(
                f"Failed to delete file from S3 storage: {error}"
            ) from error
