from sqlalchemy.orm import Session
from sqlalchemy import select
from redis import Redis
from app.db.models.webhook_subscription import WebhookSubscription
from app.services.circuit_breaker import WebhookCircuitBreaker
from app.settings import settings

# Lazy-initialized circuit breaker instance
_circuit_breaker: WebhookCircuitBreaker | None = None

def _get_circuit_breaker() -> WebhookCircuitBreaker:
    global _circuit_breaker
    if _circuit_breaker is None:
        redis_client = Redis.from_url(settings.REDIS_URL)
        _circuit_breaker = WebhookCircuitBreaker(redis_client)
    return _circuit_breaker

def create_webhook(db: Session, project_id: int, url: str, secret: str | None) -> WebhookSubscription:
    """Create a new webhook subscription for a project."""
    wh = WebhookSubscription(project_id=project_id, url=url, secret=secret, enabled=True)
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh

def list_webhooks(db: Session, project_id: int, enabled_only: bool = False) -> list[WebhookSubscription]:
    """List webhook subscriptions for a project, optionally filtering to only enabled ones."""
    q = select(WebhookSubscription).where(WebhookSubscription.project_id == project_id)
    if enabled_only:
        q = q.where(WebhookSubscription.enabled.is_(True))
    return list(db.execute(q).scalars().all())

def disable_webhook(db: Session, webhook_id: int) -> WebhookSubscription | None:
    """Disable a webhook subscription by its ID."""
    wh = db.get(WebhookSubscription, webhook_id)
    if not wh:
        return None
    wh.enabled = False
    db.commit()
    db.refresh(wh)
    return wh

def get_webhook_by_id(db: Session, webhook_id: int) -> WebhookSubscription | None:
    """Get a webhook subscription by its ID."""
    return db.get(WebhookSubscription, webhook_id)

def circuit_breaker_get_stats(db: Session, webhook_id: int) -> dict | None:
    """Get the current circuit breaker status for a given webhook."""
    wh = get_webhook_by_id(db, webhook_id)
    if not wh:
        return None
    cb = _get_circuit_breaker()
    status = cb.get_stats(wh.url)
    if not status:
        return None
    return {
        "webhook_id": webhook_id,
        "url": wh.url,
        "circuit_breaker": status
    }