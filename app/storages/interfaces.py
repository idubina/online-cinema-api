from abc import ABC, abstractmethod


class S3StorageInterface(ABC):

    @abstractmethod
    async def upload_file(
        self,
        file_name: str,
        file_data: bytes,
        content_type: str,
    ) -> None:
        """
        Upload a file to S3-compatible storage.
        """
        pass

    @abstractmethod
    async def get_file_url(
        self,
        file_name: str,
    ) -> str:
        """
        Return a public URL for a stored file.
        """
        pass

    @abstractmethod
    async def delete_file(
        self,
        file_name: str,
    ) -> None:
        """
        Delete a file from S3-compatible storage.
        """
        pass
