from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.db.models.telemetry_event import TelemetryEvent

def list_latest_events(db: Session, device_id: int, limit: int = 100) -> list[TelemetryEvent]:
    """List the latest telemetry events for a given device"""
    q = (
        select(TelemetryEvent)
        .where(TelemetryEvent.device_id == device_id)
        .order_by(desc(TelemetryEvent.ts))
        .limit(limit)
    )
    return list(db.execute(q).scalars().all())

def get_latest_event(db: Session, device_id: int) -> TelemetryEvent:
    """Get the latest telemetry event for a given device"""
    q = (
        select(TelemetryEvent)
        .where(TelemetryEvent.device_id == device_id)
        .order_by(desc(TelemetryEvent.ts))
        .limit(1)
    )
    return db.execute(q).scalars().first()

def get_events_since(db: Session, device_id: int, since_ts: float) -> list[TelemetryEvent]:
    """Get all telemetry events for a given device since a specific timestamp."""
    since_dt = datetime.fromtimestamp(since_ts, tz=timezone.utc)
    q = (
        select(TelemetryEvent)
        .where(TelemetryEvent.device_id == device_id, TelemetryEvent.ts >= since_dt)
        .order_by(desc(TelemetryEvent.ts))
    )
    return list(db.execute(q).scalars().all())