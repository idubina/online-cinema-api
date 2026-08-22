import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

security = HTTPBasic()


def verify_docs_user(
    credentials: HTTPBasicCredentials = Depends(security),
) -> None:

    username_correct = secrets.compare_digest(
        credentials.username,
        settings.DOCS_USER,
    )

    password_correct = secrets.compare_digest(
        credentials.password,
        settings.DOCS_PASSWORD,
    )

    if not username_correct or not password_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect documentation credentials.",
            headers={
                "WWW-Authenticate": "Basic",
            },
        )
