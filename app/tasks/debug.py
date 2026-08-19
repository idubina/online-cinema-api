from app.core.celery_app import celery_app


@celery_app.task
def add(x: int, y: int) -> int:
    return x + y
