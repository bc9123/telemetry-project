# app/workers/tasks/ping.py
from app.workers.celery_app import celery_app

@celery_app.task(name="app.workers.tasks.ping")
def ping():
    """Simple task to test worker responsiveness."""
    return "pong"
