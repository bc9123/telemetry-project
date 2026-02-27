from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.org import OrgCreate, OrgOut
from app.services.org_service import create_org_service

router = APIRouter(prefix="/orgs", tags=["orgs"])

@router.post("", response_model=OrgOut, status_code=201)
def create_org(payload: OrgCreate, db: Session = Depends(get_db)):
    """Create a new organization"""
    return create_org_service(db, name=payload.name)
