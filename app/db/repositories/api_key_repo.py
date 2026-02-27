from sqlalchemy.orm import Session
from app.db.models.api_key import ApiKey

def create_api_key(db: Session, project_id: int, prefix: str, hashed_secret: str) -> ApiKey:
    """Create a new API key for a project."""
    key = ApiKey(project_id=project_id, prefix=prefix, hashed_secret=hashed_secret)
    db.add(key)
    db.commit()
    db.refresh(key)
    return key