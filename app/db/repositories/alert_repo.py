# app/db/repositories/alert_repo.py
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.db.models.alert import Alert

def get_latest_alert_time(db: Session, device_id: int, rule_id: int) -> datetime | None:
    """
    Get the most recent Alert.triggered_at for this device and rule.
    Returns None if no such alert exists.
    """
    q = (
        select(Alert.triggered_at)
        .where(Alert.device_id == device_id, Alert.rule_id == rule_id)
        .order_by(desc(Alert.triggered_at))
        .limit(1)
    )
    return db.execute(q).scalars().first()

def create_alert(db: Session, alert: Alert, commit: bool = True) -> Alert:
    """
    Persist an Alert.
    If commit=False, the caller must commit the transaction.
    """
    db.add(alert)
    if commit:
        db.commit()
        db.refresh(alert)
    else:
        db.flush()
        db.refresh(alert)
    return alert

def list_alerts_for_project_devices(db: Session, device_ids: list[int], limit: int = 100) -> list[Alert]:
    """
    List recent alerts for a list of device IDs. Used by the project activity feed.
    If device_ids is empty, returns an empty list.
    Alerts are ordered by triggered_at descending.
    """
    if not device_ids:
        return []
    q = (
        select(Alert)
        .where(Alert.device_id.in_(device_ids))
        .order_by(desc(Alert.triggered_at))
        .limit(limit)
    )
    return list(db.execute(q).scalars().all())

def list_alerts_for_device(db: Session, device_id: int, limit: int = 100) -> list[Alert]:
    """
    List recent alerts for a single device.
    If no alerts exist for this device, returns an empty list.
    Alerts are ordered by triggered_at descending.
    """
    q = (
        select(Alert)
        .where(Alert.device_id == device_id)
        .order_by(desc(Alert.triggered_at))
        .limit(limit)
    )
    return list(db.execute(q).scalars().all())
