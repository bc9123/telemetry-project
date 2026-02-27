from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.rate_limits import RateLimits, limiter
from app.schemas.device import DeviceCreate, DeviceOut
from app.schemas.device_tags import DeviceTagsUpdate
from app.services.device_service import (
    add_device_tags_service, 
    create_device_service, 
    get_device_service,
    list_devices_service,
    delete_device_service,
    remove_device_tags_service, 
    set_device_tags_service
)

router = APIRouter(prefix="/projects/{project_id}/devices", tags=["devices"])

@router.post("", response_model=DeviceOut, status_code=201)
@limiter.limit(RateLimits.DEVICE_CREATE)
def create_device(request: Request, project_id: int, payload: DeviceCreate, db: Session = Depends(get_db)):
    """Create a new device in the project"""
    return create_device_service(
        db, 
        project_id=project_id, 
        external_id=payload.external_id, 
        name=payload.name,
        tags=payload.tags
    )

@router.get("", response_model=list[DeviceOut], status_code=200)
def list_devices(project_id: int, db: Session = Depends(get_db)):
    """List all devices in the project"""
    return list_devices_service(db, project_id=project_id)

@router.get("/{device_id}", response_model=DeviceOut, status_code=200)
def get_device(project_id: int, device_id: int, db: Session = Depends(get_db)):
    """Get a specific device by ID"""
    return get_device_service(db, device_id=device_id)

@router.delete("/{device_id}", status_code=204)
def delete_device(project_id: int, device_id: int, db: Session = Depends(get_db)):
    """Delete a device by ID"""
    return delete_device_service(db, device_id=device_id)

@router.patch("/{device_id}/tags")
def update_device_tags(project_id: int, device_id: int, payload: DeviceTagsUpdate, db: Session = Depends(get_db)):
    """Replace all tags on a device"""
    device = set_device_tags_service(db, device_id=device_id, tags=payload.tags)
    return {"device_id": device.id, "tags": device.tags}

@router.post("/{device_id}/tags")
def add_device_tags(project_id: int, device_id: int, payload: DeviceTagsUpdate, db: Session = Depends(get_db)):
    """Add tags to a device (preserves existing tags)"""
    device = add_device_tags_service(db, device_id=device_id, tags=payload.tags)
    return {"device_id": device.id, "tags": device.tags}

@router.delete("/{device_id}/tags")
def remove_device_tags(project_id: int, device_id: int, payload: DeviceTagsUpdate, db: Session = Depends(get_db)):
    """Remove specific tags from a device"""
    device = remove_device_tags_service(db, device_id=device_id, tags=payload.tags)
    return {"device_id": device.id, "tags": device.tags}