from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.repositories.project_repo import get_project
from app.db.repositories.webhook_repo import create_webhook, list_webhooks, disable_webhook, get_webhook_by_id, circuit_breaker_get_stats

def create_webhook_service(db: Session, project_id: int, url: str, secret: str | None):
    """Create a new webhook for a specific project."""
    if not get_project(db, project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return create_webhook(db, project_id=project_id, url=url, secret=secret)

def list_webhooks_service(db: Session, project_id: int):
    """List all webhooks for a specific project."""
    if not get_project(db, project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return list_webhooks(db, project_id=project_id, enabled_only=False)

def disable_webhook_service(db: Session, webhook_id: int):
    """Disable a specific webhook by its ID."""
    wh = disable_webhook(db, webhook_id=webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="webhook not found")
    return wh

def get_webhook_by_id_service(db: Session, webhook_id: int):
    """Get a specific webhook by its ID."""
    wh = get_webhook_by_id(db, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="webhook not found")
    return wh

def get_circuit_status_service(db: Session, webhook_id: int):
    """Get the circuit breaker status for a specific webhook."""
    status = circuit_breaker_get_stats(db, webhook_id)
    if not status:
        raise HTTPException(status_code=404, detail="webhook not found or no circuit breaker data")
    return status