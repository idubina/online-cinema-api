from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "online_cinema",
    broker=settings.CELERY_BROKER_URL,
    include=["app.tasks.debug"],
)
