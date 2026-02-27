from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.repositories.org_repo import get_org
from app.db.repositories.project_repo import create_project

def create_project_service(db: Session, org_id: int, name: str):
    """Create a new project within a specific organization."""
    if not get_org(db, org_id):
        raise HTTPException(status_code=404, detail="org not found")
    return create_project(db, org_id=org_id, name=name)
