from sqlalchemy.orm import Session
from app.db.models.org import Org

def create_org(db: Session, name: str) -> Org:
    """Create a new organization."""
    org = Org(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org

def get_org(db: Session, org_id: int) -> Org | None:
    """Get an organization by its ID."""
    return db.get(Org, org_id)