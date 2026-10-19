"""
Celery application definition. Run the worker with:
    celery -A app.celery_app.celery_app worker --loglevel=info

Using a real task queue (instead of FastAPI BackgroundTasks) means ingestion
survives an API pod restart, can be scaled independently of the API
(see k8s/worker-deployment.yaml + its own HPA), and gets retries for free.
"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "docklight",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
