from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.security import generate_api_key
from app.db.repositories.project_repo import get_project
from app.db.repositories.api_key_repo import create_api_key

def create_api_key_service(db: Session, project_id: int):
    """Create a new API key for a specific project."""
    if not get_project(db, project_id):
        raise HTTPException(status_code=404, detail="project not found")

    raw, prefix, hashed = generate_api_key()
    create_api_key(db, project_id=project_id, prefix=prefix, hashed_secret=hashed)
    return raw, prefix
