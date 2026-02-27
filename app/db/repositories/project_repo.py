from sqlalchemy.orm import Session
from app.db.models.project import Project

def create_project(db: Session, name: str, org_id: int) -> Project:
    """Create a new project."""
    project = Project(name=name, org_id=org_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def get_project(db: Session, project_id: int) -> Project | None:
    """Get a project by its ID."""
    return db.get(Project, project_id)