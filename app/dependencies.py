from typing import Annotated
from fastapi import Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

from app.core.config import settings
from app.notifications.email_sender import EmailSender
from app.notifications.interfaces import EmailSenderInterface


import jwt

from fastapi.security import OAuth2PasswordBearer

from app.core.security import JWTManager
from app.models.accounts import UserModel, UserGroupEnum
from app.repositories import accounts

SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_email_sender() -> EmailSenderInterface:
    return EmailSender(
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        sender_email=settings.SMTP_FROM_EMAIL,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        start_tls=settings.SMTP_START_TLS,
    )


EmailSenderDep = Annotated[
    EmailSenderInterface,
    Depends(get_email_sender),
]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/accounts/login/")


async def get_current_user(
    db: SessionDep,
    token: str = Depends(oauth2_scheme),
) -> UserModel:
    try:
        payload = JWTManager.decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        )

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        )

    user = await accounts.get_user_by_id(
        db=db,
        id=user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return user


CurrentUserDep = Annotated[
    UserModel,
    Depends(get_current_user),
]


def require_roles(*allowed_roles: UserGroupEnum):
    async def dependency(
        current_user: CurrentUserDep,
    ) -> UserModel:
        if current_user.group.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return dependency


AdminDep = Annotated[
    UserModel,
    Depends(
        require_roles(
            UserGroupEnum.ADMIN,
        )
    ),
]

ModeratorDep = Annotated[
    UserModel,
    Depends(
        require_roles(
            UserGroupEnum.MODERATOR,
            UserGroupEnum.ADMIN,
        )
    ),
]
