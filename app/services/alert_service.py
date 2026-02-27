# app/services/alert_service.py
from sqlalchemy.orm import Session
from app.db.repositories.alert_repo import list_alerts_for_device, list_alerts_for_project_devices
from app.db.repositories.device_repo import list_device_ids_for_project

def list_device_alerts_service(db: Session, device_id: int, limit: int = 100):
    """List alerts for a specific device."""
    return list_alerts_for_device(db, device_id=device_id, limit=limit)

def list_project_alerts_service(db: Session, project_id: int, limit: int = 100):
    """List alerts for all devices in a specific project."""
    device_ids = list_device_ids_for_project(db, project_id=project_id)
    return list_alerts_for_project_devices(db, device_ids=device_ids, limit=limit)
