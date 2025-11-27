from celery import Celery
from src.config.settings import settings

# Use REDIS_URL from settings or fallback to local Redis default
broker = settings.REDIS_URL or "redis://localhost:6379/0"
backend = settings.REDIS_URL or broker

app = Celery(
    "aiagents_worker",
    broker=broker,
    backend=backend,
)

app.conf.task_default_queue = "aiagents"
app.conf.result_expires = 3600
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]


# Import tasks so Celery autodiscovers them when worker starts
# (this file is intentionally minimal)
try:
    import src.workers.tasks  # noqa: F401
except Exception:
    # Avoid failing imports during migrations or other CLI operations
    pass
