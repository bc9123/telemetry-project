# app/workers/tasks/webhook_delivery.py
import json
import hmac
import structlog
import hashlib
from datetime import datetime, timezone
import random
import httpx
from redis import Redis
from celery.exceptions import MaxRetriesExceededError

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.alert import Alert
from app.db.models.device import Device
from app.services.circuit_breaker import WebhookCircuitBreaker
from app.settings import settings
from app.db.repositories.webhook_repo import list_webhooks, get_webhook_by_id
from app.db.repositories.webhook_delivery_repo import (
    ensure_delivery_row,
    get_delivery_by_id,
    try_mark_sending,
    mark_success,
    mark_failed,
    mark_retrying,
)

# Global Redis client and circuit breaker
redis_client = Redis.from_url(settings.REDIS_URL)
circuit_breaker = WebhookCircuitBreaker(redis_client)
logger = structlog.get_logger(__name__)

def _sign(secret: str, timestamp: str, body: str) -> str:
    """Generate HMAC SHA256 signature for webhook payload."""
    msg = f"{timestamp}.{body}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

def _countdown(retries: int) -> int:
    """Calculate exponential backoff delay with jitter for retries."""
    base = 5
    cap = 60 * 30
    delay = min(cap, base * (2 ** retries))
    jitter = random.randint(0, min(30, delay))
    return delay + jitter

@celery_app.task(name="app.workers.tasks.enqueue_webhooks_for_alert")
def enqueue_webhooks_for_alert(alert_id: int) -> int:
    """Enqueue webhook deliveries for all relevant webhooks for a specific alert."""
    db = SessionLocal()
    try:
        alert = db.get(Alert, alert_id)
        if not alert:
            return 0

        device = db.get(Device, alert.device_id)
        if not device:
            return 0

        webhooks = list_webhooks(db, project_id=device.project_id, enabled_only=True)
        if not webhooks:
            return 0

        delivery_ids: list[int] = []
        for wh in webhooks:
            d = ensure_delivery_row(
                db,
                project_id=device.project_id,
                alert_id=alert_id,
                webhook_id=wh.id,
            )
            delivery_ids.append(d.id)

        for did in delivery_ids:
            deliver_webhook.delay(did)

        return len(delivery_ids)
    finally:
        db.close()

@celery_app.task(bind=True, name="app.workers.tasks.deliver_webhook", max_retries=8)
def deliver_webhook(self, delivery_id: int) -> str:
    """Deliver a single webhook for a specific delivery ID. Handles retries with exponential backoff and circuit breaker logic."""
    logger.info(
        "webhook_delivery_started",
        delivery_id=delivery_id,
        attempt=self.request.retries + 1
    )

    db = SessionLocal()
    try:
        delivery = get_delivery_by_id(db, delivery_id)
        if not delivery:
            return "delivery_missing"

        if delivery.status == "success":
            return "already_success"

        if not try_mark_sending(db, delivery.id):
            return "in_progress_or_already_handled"

        alert = db.get(Alert, delivery.alert_id)
        if not alert:
            mark_failed(db, delivery.id, None, "alert_missing")
            return "alert_missing"

        device = db.get(Device, alert.device_id)
        if not device:
            mark_failed(db, delivery.id, None, "device_missing")
            return "device_missing"

        wh = get_webhook_by_id(db, delivery.webhook_id)
        if not wh or not wh.enabled:
            mark_failed(db, delivery.id, None, "webhook_missing_or_disabled")
            return "webhook_missing_or_disabled"

        if circuit_breaker.is_open(wh.url):
            logger.warning(
                "webhook_circuit_open",
                delivery_id=delivery_id,
                webhook_id=wh.id,
                url=wh.url
            )
            mark_retrying(db, delivery.id, None, f"circuit_open:{wh.url}")
            try:
                raise self.retry(countdown=_countdown(self.request.retries))
            except MaxRetriesExceededError:
                mark_failed(db, delivery.id, None, "max_retries_exceeded:circuit_open")
                return "failed_max_retries"

        payload = {
            "alert_id": alert.id,
            "device_id": alert.device_id,
            "rule_id": alert.rule_id,
            "triggered_at": alert.triggered_at.isoformat(),
            "details": alert.details,
        }
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        ts = datetime.now(timezone.utc).isoformat()

        headers = {"Content-Type": "application/json", "X-Telemetry-Timestamp": ts}
        if wh.secret:
            headers["X-Telemetry-Signature"] = _sign(wh.secret, ts, body)

        timeout = httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=5.0)

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(wh.url, content=body, headers=headers)

            code = resp.status_code
            retryable = (code == 429) or (code == 408) or (code >= 500)
            
            if code >= 200 and code < 300:
                logger.info(
                    "webhook_delivered",
                    delivery_id=delivery_id,
                    webhook_id=wh.id,
                    url=wh.url,
                    status_code=code,
                    attempt=self.request.retries + 1
                )
                circuit_breaker.record_success(wh.url)  # Record success
                mark_success(db, delivery.id, code)
                return "success"

            elif code == 429 or code == 408 or code >= 500:
                logger.warning(
                    "webhook_retryable_error",
                    delivery_id=delivery_id,
                    webhook_id=wh.id,
                    url=wh.url,
                    status_code=code,
                    attempt=self.request.retries + 1,
                    max_retries=self.max_retries
                )
                circuit_breaker.record_failure(wh.url)  # Record failure
                mark_retrying(db, delivery.id, code, f"retryable_status_{code}")
                raise self.retry(countdown=_countdown(self.request.retries))

            else:
                logger.error(
                    "webhook_non_retryable_error",
                    delivery_id=delivery_id,
                    webhook_id=wh.id,
                    url=wh.url,
                    status_code=code
                )
                circuit_breaker.record_failure(wh.url)  # Record failure
                mark_failed(db, delivery.id, code, f"non_retryable_status_{code}")
                return "failed_non_retryable"

        except httpx.HTTPError as e:
            circuit_breaker.record_failure(wh.url)  # Record failure
            mark_retrying(db, delivery.id, None, f"http_error:{type(e).__name__}")
            try:
                raise self.retry(exc=e, countdown=_countdown(self.request.retries))
            except MaxRetriesExceededError:
                mark_failed(db, delivery.id, None, "max_retries_exceeded:http_error")
                return "failed_max_retries"

        except MaxRetriesExceededError:
            mark_failed(db, delivery.id, None, "max_retries_exceeded")
            return "failed_max_retries"

    finally:
        db.close()
        logger.info(
            "webhook_delivery_finished",
            delivery_id=delivery_id,
            attempt=self.request.retries + 1
        )