from datetime import datetime, timezone, timedelta
from enum import StrEnum

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using the recommended password hasher.

    Args:
        password: Plain-text password.

    Returns:
        Hashed password.
    """
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plain-text password against a stored password hash.

    Args:
        plain_password: Plain-text password provided by the user.
        hashed_password: Password hash stored in the database.

    Returns:
        True if the password matches, otherwise False.
    """
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class JWTManager:
    @staticmethod
    def create_access_token(user_id: int) -> str:
        now = datetime.now(timezone.utc)

        payload = {
            "sub": str(user_id),
            "type": TokenType.ACCESS,
            "iat": now,
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        }

        return jwt.encode(
            payload,
            settings.SECRET_KEY_ACCESS,
            algorithm=settings.JWT_SIGNING_ALGORITHM,
        )

    @staticmethod
    def create_refresh_token(user_id: int) -> str:
        now = datetime.now(timezone.utc)

        payload = {
            "sub": str(user_id),
            "type": TokenType.REFRESH,
            "iat": now,
            "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        }

        return jwt.encode(
            payload,
            settings.SECRET_KEY_REFRESH,
            algorithm=settings.JWT_SIGNING_ALGORITHM,
        )

    @staticmethod
    def decode_access_token(token: str) -> dict:
        return JWTManager._decode_token(
            token=token,
            secret_key=settings.SECRET_KEY_ACCESS,
            expected_type=TokenType.ACCESS,
        )

    @staticmethod
    def decode_refresh_token(token: str) -> dict:
        return JWTManager._decode_token(
            token=token,
            secret_key=settings.SECRET_KEY_REFRESH,
            expected_type=TokenType.REFRESH,
        )

    @staticmethod
    def _decode_token(
        token: str,
        secret_key: str,
        expected_type: TokenType,
    ) -> dict:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.JWT_SIGNING_ALGORITHM],
            options={
                "require": [
                    "sub",
                    "type",
                    "iat",
                    "exp",
                ]
            },
        )

        if payload["type"] != expected_type:
            raise jwt.InvalidTokenError(f"Expected {expected_type} token.")

        return payload
