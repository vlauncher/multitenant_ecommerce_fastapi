from celery import Celery
from core.config import settings

# Use Redis for production/development
broker_url = settings.REDIS_URL
backend_url = settings.REDIS_URL

# Create Celery app
celery_app = Celery(
    "multitenant_ecommerce",
    broker=broker_url,
    backend=backend_url,
    include=["tasks.email_tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Don't use eager mode - use actual Redis
    task_always_eager=False,
    task_eager_propagates=False,
)
