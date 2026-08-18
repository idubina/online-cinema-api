from typing import Annotated
from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

from app.core.config import settings
from app.notifications.email_sender import EmailSender
from app.notifications.interfaces import EmailSenderInterface

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
