from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.models.device import Device
from app.db.repositories.project_repo import get_project
from app.db.repositories.device_repo import (
    add_device_tags, 
    create_device, 
    get_device,
    list_devices,
    delete_device,
    set_device_tags, 
    remove_device_tags
)

def create_device_service(db: Session, project_id: int, external_id: str, name: str, tags: list[str] = None):
    """Create a new device in a project with optional tags"""
    if not get_project(db, project_id):
        raise HTTPException(status_code=404, detail="project not found")
    if tags is None:
        tags = []
    try:
        return create_device(db, project_id=project_id, external_id=external_id, name=name, tags=tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

def get_device_service(db: Session, device_id: int) -> Device:
    """Get a single device by ID"""
    device = get_device(db, device_id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    return device

def list_devices_service(db: Session, project_id: int):
    """List all devices in a project"""
    if not get_project(db, project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return list_devices(db, project_id=project_id)

def delete_device_service(db: Session, device_id: int):
    """Delete a device by ID"""
    if not delete_device(db, device_id=device_id):
        raise HTTPException(status_code=404, detail="device not found")

def set_device_tags_service(db: Session, device_id: int, tags: list[str]):
    """Replace device tags completely"""
    device = set_device_tags(db, device_id=device_id, tags=tags)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    return device

def add_device_tags_service(db: Session, device_id: int, tags: list[str]):
    """Add tags to a device (preserving existing tags)"""
    device = add_device_tags(db, device_id=device_id, tags=tags)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    return device

def remove_device_tags_service(db: Session, device_id: int, tags: list[str]):
    """Remove specific tags from a device"""
    device = remove_device_tags(db, device_id=device_id, tags=tags)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    return device