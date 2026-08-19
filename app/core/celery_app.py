from datetime import timedelta

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "online_cinema",
    broker=settings.CELERY_BROKER_URL,
    include=["app.tasks.cleanup"],
)

celery_app.conf.beat_schedule = {
    "cleanup-expired-activation-tokens": {
        "task": "app.tasks.cleanup.cleanup_expired_activation_tokens",
        "schedule": timedelta(hours=1),
    },
}
