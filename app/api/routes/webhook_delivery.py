from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.api.deps import get_db, get_project_id_from_api_key
from app.db.models.webhook_delivery import WebhookDelivery
from app.schemas.webhook_delivery import WebhookDeliveryOut, WebhookDeliveryStatus

router = APIRouter(tags=["webhook-deliveries"])

@router.get("/projects/{project_id}/webhook-deliveries", response_model=list[WebhookDeliveryOut])
def list_deliveries(
    project_id: int,
    status: WebhookDeliveryStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    auth_project_id: int = Depends(get_project_id_from_api_key),
):
    """List webhook deliveries for a project, optionally filtered by status"""
    if project_id != auth_project_id:
        return []

    q = select(WebhookDelivery).where(WebhookDelivery.project_id == project_id)
    if status:
        q = q.where(WebhookDelivery.status == status)

    q = q.order_by(desc(WebhookDelivery.created_at)).limit(limit)
    return list(db.execute(q).scalars().all())
