from sqlalchemy.orm import Session
from app.db.repositories.org_repo import create_org

def create_org_service(db: Session, name: str):
    """Create a new organization."""
    return create_org(db, name=name)
