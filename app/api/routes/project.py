from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.project import ProjectCreate, ProjectOut
from app.services.project_service import create_project_service

router = APIRouter(prefix="/orgs/{org_id}/projects", tags=["projects"])

@router.post("", response_model=ProjectOut, status_code=201)
def create_project(org_id: int, payload: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project within the specified organization"""
    return create_project_service(db, org_id=org_id, name=payload.name)
