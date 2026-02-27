# app/workers/tasks/evaluate_rules.py
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.evaluation_service import evaluate_rules_for_device
from app.workers.tasks.webhook_delivery import enqueue_webhooks_for_alert

@celery_app.task(name="app.workers.tasks.evaluate_rules_for_device")
def evaluate_rules_for_device_task(device_id: int) -> list[int]:
    """Evaluate rules for a specific device and enqueue webhooks for any triggered alerts."""
    db = SessionLocal()
    try:
        alert_ids = evaluate_rules_for_device(db, device_id=device_id)
        for aid in alert_ids:
            enqueue_webhooks_for_alert.delay(aid)
        return alert_ids
    finally:
        db.close()

