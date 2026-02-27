from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.deps import get_db, get_project_id_from_api_key
from app.api.rate_limits import RateLimits, limiter
from app.db.models.device import Device
from app.schemas.telemetry import TelemetryBatchIn, TelemetryEventOut
from app.services.telemetry_service import get_events_since_service, get_latest_event_service, list_latest_events_service
from app.workers.tasks.ingest import ingest_events

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

@router.post("", status_code=202)
@limiter.limit(RateLimits.INGESTION)
def ingest_telemetry(
    request: Request,
    payload: TelemetryBatchIn,
    db: Session = Depends(get_db),
    project_id: int = Depends(get_project_id_from_api_key),
):
    """Ingest a batch of telemetry events for a device"""
    if not payload.events:
        raise HTTPException(status_code=400, detail="events cannot be empty")
    if len(payload.events) > 5000:
        raise HTTPException(status_code=400, detail="too many events (max 5000)")

    device = db.execute(
        select(Device).where(
            Device.project_id == project_id,
            Device.external_id == payload.device_external_id,
        )
    ).scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="device not found")

    # serialize to plain dicts for Celery JSON serializer
    events = [{"ts": e.ts.isoformat(), "data": e.data} for e in payload.events]
    ingest_events.delay(device.id, events)

    return {"queued": len(events), "device_id": device.id}

@router.get("/devices/{device_id}/telemetry", response_model=list[TelemetryEventOut])
def list_latest(
    device_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List the latest telemetry events for a device"""
    return list_latest_events_service(db, device_id=device_id, limit=limit)

@router.get("/devices/{device_id}/telemetry/latest", response_model=TelemetryEventOut)
def get_latest(
    device_id: int,
    db: Session = Depends(get_db),
):
    """Get the latest telemetry event for a device"""
    return get_latest_event_service(db, device_id=device_id)

@router.get("/devices/{device_id}/telemetry/since", response_model=list[TelemetryEventOut])
def get_events_since(
    device_id: int,
    since_ts: float = Query(..., description="Unix timestamp in seconds"),
    db: Session = Depends(get_db),
):
    """Get telemetry events for a device since a specific timestamp"""
    return get_events_since_service(db, device_id=device_id, since_ts=since_ts)