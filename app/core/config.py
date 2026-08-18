from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI backend for online cinema"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    POSTGRES_TEST_DB: str
    POSTGRES_TEST_HOST: str
    POSTGRES_TEST_PORT: int

    SECRET_KEY_ACCESS: str
    SECRET_KEY_REFRESH: str
    JWT_SIGNING_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def async_sqlalchemy_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    @property
    def async_sqlalchemy_database_test_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_TEST_HOST}:"
            f"{self.POSTGRES_TEST_PORT}/"
            f"{self.POSTGRES_TEST_DB}"
        )

    @property
    def sync_sqlalchemy_database_url(self) -> str:
        return (
            f"postgresql+psycopg://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )


settings = Settings()
