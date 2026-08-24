from email.message import EmailMessage

import aiosmtplib

from app.notifications.interfaces import EmailSenderInterface


class EmailSender(EmailSenderInterface):
    def __init__(
        self,
        hostname: str,
        port: int,
        sender_email: str,
        username: str | None = None,
        password: str | None = None,
        start_tls: bool = False,
    ):
        self._hostname = hostname
        self._port = port
        self._sender_email = sender_email
        self._username = username
        self._password = password
        self._start_tls = start_tls

    async def _send_email(
        self,
        recipient: str,
        subject: str,
        content: str,
    ) -> None:
        message = EmailMessage()
        message["From"] = self._sender_email
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(content)

        await aiosmtplib.send(
            message,
            hostname=self._hostname,
            port=self._port,
            username=self._username or None,
            password=self._password or None,
            start_tls=self._start_tls,
        )

    async def send_activation_email(
        self,
        email: str,
        activation_link: str,
    ) -> None:
        await self._send_email(
            recipient=email,
            subject="Account Activation",
            content=(
                "Welcome to Online Cinema!\n\n"
                "Activate your account using the link below:\n"
                f"{activation_link}"
            ),
        )

    async def send_activation_complete_email(
        self,
        email: str,
        login_link: str,
    ) -> None:
        await self._send_email(
            recipient=email,
            subject="Account Activated",
            content=(
                "Your account has been successfully activated.\n\n"
                "You can log in here:\n"
                f"{login_link}"
            ),
        )

    async def send_password_reset_email(
        self,
        email: str,
        reset_link: str,
    ) -> None:
        await self._send_email(
            recipient=email,
            subject="Password Reset",
            content=(
                "A password reset was requested for your account.\n\n"
                "Reset your password using the link below:\n"
                f"{reset_link}"
            ),
        )

    async def send_password_reset_complete_email(
        self,
        email: str,
        login_link: str,
    ) -> None:
        await self._send_email(
            recipient=email,
            subject="Password Reset Successful",
            content=(
                "Your password has been successfully changed.\n\n"
                "You can log in here:\n"
                f"{login_link}"
            ),
        )
