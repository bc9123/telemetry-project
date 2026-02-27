from fastapi import APIRouter, Depends, Request
from app.api.rate_limits import RateLimits, limiter
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.api_key import ApiKeyCreateOut
from app.services.api_key_service import create_api_key_service

router = APIRouter(prefix="/projects/{project_id}/api-keys", tags=["api-keys"])

@router.post("", response_model=ApiKeyCreateOut, status_code=201)
@limiter.limit(RateLimits.API_KEY_CREATE)
def create_api_key(request: Request, project_id: int, db: Session = Depends(get_db)):
    """Create a new API key for the specified project"""
    raw, prefix = create_api_key_service(db, project_id=project_id)
    return ApiKeyCreateOut(api_key=raw, prefix=prefix, project_id=project_id)
