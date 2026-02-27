from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.rate_limits import RateLimits, limiter
from app.schemas.webhook import WebhookCreate, WebhookOut
from app.services.webhook_service import create_webhook_service, get_circuit_status_service, get_webhook_by_id_service, list_webhooks_service, disable_webhook_service

router = APIRouter(tags=["webhooks"])

@router.post("/projects/{project_id}/webhooks", response_model=WebhookOut, status_code=201)
@limiter.limit(RateLimits.WEBHOOK_CREATE)
def create_webhook(request: Request, project_id: int, payload: WebhookCreate, db: Session = Depends(get_db)):
    """Create a new webhook for a project"""
    return create_webhook_service(db, project_id=project_id, url=str(payload.url), secret=payload.secret)

@router.get("/projects/{project_id}/webhooks", response_model=list[WebhookOut])
def list_webhooks(project_id: int, db: Session = Depends(get_db)):
    """List all webhooks for a project"""
    return list_webhooks_service(db, project_id=project_id)

@router.post("/webhooks/{webhook_id}/disable", response_model=WebhookOut)
def disable_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Disable a specific webhook by its ID"""
    return disable_webhook_service(db, webhook_id=webhook_id)

@router.get("/webhooks/{webhook_id}", response_model=WebhookOut)
def get_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Get details of a specific webhook by its ID"""
    return get_webhook_by_id_service(db, webhook_id)

@router.get("/webhooks/{webhook_id}/circuit-status")
def get_circuit_status(webhook_id: int, db: Session = Depends(get_db)):
    """Get the current circuit breaker status for a specific webhook by its ID"""
    return get_circuit_status_service(db, webhook_id)