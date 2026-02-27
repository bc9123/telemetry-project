from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models.webhook_delivery import WebhookDelivery

def get_delivery(db: Session, alert_id: int, webhook_id: int) -> WebhookDelivery | None:
    """Get the delivery record for a specific alert and webhook, if it exists."""
    q = select(WebhookDelivery).where(
        WebhookDelivery.alert_id == alert_id,
        WebhookDelivery.webhook_id == webhook_id,
    )
    return db.execute(q).scalars().first()

def get_delivery_by_id(db: Session, delivery_id: int) -> WebhookDelivery | None:
    """Get a delivery record by its ID."""
    q = select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
    return db.execute(q).scalars().first()


def ensure_delivery_row(db: Session, project_id: int, alert_id: int, webhook_id: int) -> WebhookDelivery:
    """Ensure that a delivery record exists for the given alert and webhook, creating it if necessary."""
    now = datetime.now(timezone.utc)

    stmt = (
        pg_insert(WebhookDelivery)
        .values(
            project_id=project_id,
            alert_id=alert_id,
            webhook_id=webhook_id,
            status="pending",
            attempts=0,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            constraint="uq_delivery_alert_webhook",
            set_={"updated_at": WebhookDelivery.updated_at},  # no-op update, but allows RETURNING
        )
        .returning(WebhookDelivery.id)
    )

    delivery_id = db.execute(stmt).scalar_one()
    return get_delivery_by_id(db, delivery_id=delivery_id)

from datetime import datetime, timezone, timedelta
from sqlalchemy import update, or_, and_

SENDING_STALE_AFTER = timedelta(seconds=120)

def try_mark_sending(db: Session, delivery_id: int) -> bool:
    """Attempt to mark a delivery as 'sending' if it's currently 'pending' or 'retrying', or if it's 'sending' but stale."""
    now = datetime.now(timezone.utc)
    stale_before = now - SENDING_STALE_AFTER

    stmt = (
        update(WebhookDelivery)
        .where(
            WebhookDelivery.id == delivery_id,
            or_(
                WebhookDelivery.status.in_(["pending", "retrying"]),
                and_(
                    WebhookDelivery.status == "sending",
                    WebhookDelivery.updated_at < stale_before,
                ),
            ),
        )
        .values(
            status="sending",
            attempts=WebhookDelivery.attempts + 1,
            updated_at=now,
            last_error=None,
            last_status_code=None,
        )
        .returning(WebhookDelivery.id)
    )

    updated = db.execute(stmt).scalar_one_or_none()
    db.commit()
    return updated is not None

def mark_success(db: Session, delivery_id: int, status_code: int):
    """Mark a delivery as successful, setting the final status code and delivered timestamp."""
    now = datetime.now(timezone.utc)
    db.execute(
        update(WebhookDelivery)
        .where(WebhookDelivery.id == delivery_id, WebhookDelivery.status == "sending")
        .values(status="success", last_status_code=status_code, delivered_at=now, updated_at=now)
    )
    db.commit()

def mark_failed(db: Session, delivery_id: int, status_code: int | None, error: str):
    """Mark a delivery as failed, setting the final status code and error message."""
    now = datetime.now(timezone.utc)
    db.execute(
        update(WebhookDelivery)
        .where(WebhookDelivery.id == delivery_id, WebhookDelivery.status == "sending")
        .values(status="failed", last_status_code=status_code, last_error=error, updated_at=now)
    )
    db.commit()

def mark_retrying(db: Session, delivery_id: int, status_code: int | None, error: str):
    """Mark a delivery as retrying, setting the last status code and error message."""
    now = datetime.now(timezone.utc)
    db.execute(
        update(WebhookDelivery)
        .where(WebhookDelivery.id == delivery_id, WebhookDelivery.status == "sending")
        .values(status="retrying", last_status_code=status_code, last_error=error, updated_at=now)
    )
    db.commit()
