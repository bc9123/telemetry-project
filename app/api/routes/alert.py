# app/api/routes/alerts.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.alert import AlertOut
from app.services.alert_service import list_device_alerts_service, list_project_alerts_service

router = APIRouter(tags=["alerts"])

@router.get("/devices/{device_id}/alerts", response_model=list[AlertOut])
def list_device_alerts(
    device_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List alerts for a specific device."""
    return list_device_alerts_service(db, device_id=device_id, limit=limit)

@router.get("/projects/{project_id}/alerts", response_model=list[AlertOut])
def list_project_alerts(
    project_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List alerts for a specific project."""
    return list_project_alerts_service(db, project_id=project_id, limit=limit)
