from sqlalchemy.orm import Session
from app.db.repositories.telemetry_repo import list_latest_events
from app.db.repositories.telemetry_repo import get_latest_event
from app.db.repositories.telemetry_repo import get_events_since

def list_latest_events_service(db: Session, device_id: int, limit: int = 100):
    """List the latest telemetry events for a specific device."""
    return list_latest_events(db, device_id=device_id, limit=limit)

def get_latest_event_service(db: Session, device_id: int):
    """Get the latest telemetry event for a specific device."""
    return get_latest_event(db, device_id=device_id)

def get_events_since_service(db: Session, device_id: int, since_ts: float):
    """Get telemetry events for a specific device since a given timestamp."""
    return get_events_since(db, device_id=device_id, since_ts=since_ts)