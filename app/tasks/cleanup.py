from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.database import SyncSessionLocal
from app.models.accounts import ActivationTokenModel


def delete_expired_activation_tokens(db: Session) -> int:
    result = db.execute(
        delete(ActivationTokenModel).where(
            ActivationTokenModel.expires_at < datetime.now(timezone.utc)
        )
    )

    db.commit()

    return result.rowcount or 0


@celery_app.task
def cleanup_expired_activation_tokens() -> int:
    with SyncSessionLocal() as db:
        return delete_expired_activation_tokens(db)
