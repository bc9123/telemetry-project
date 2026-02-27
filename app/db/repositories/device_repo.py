from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.device import Device

def create_device(db: Session, project_id: int, external_id: str, name: str, tags: list[str] = None) -> Device:
    """Create a new device for a project."""
    existing = db.execute(
        select(Device).where(
            Device.project_id == project_id,
            Device.external_id == external_id
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("external_id must be unique within the project")
    device = Device(project_id=project_id, external_id=external_id, name=name, tags=tags)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device

def list_devices(db: Session, project_id: int) -> list[Device]:
    """List all devices for a project."""
    return list(db.execute(select(Device).where(Device.project_id == project_id)).scalars().all())

def get_device(db: Session, device_id: int) -> Device | None:
    """Get a device by its ID."""
    return db.get(Device, device_id)

def list_device_ids_for_project(db: Session, project_id: int) -> list[int]:
    """List all device IDs for a project."""
    q = select(Device.id).where(Device.project_id == project_id)
    return list(db.execute(q).scalars().all())

def delete_device(db: Session, device_id: int) -> bool:
    """Delete a device by its ID."""
    device = db.get(Device, device_id)
    if not device:
        return None
    db.delete(device)
    db.commit()
    return True

def set_device_tags(db: Session, device_id: int, tags: list[str]) -> Device | None:
    """Set the tags for a device, replacing any existing tags."""
    device = db.get(Device, device_id)
    if not device:
        return None

    cleaned = []
    seen = set()
    for t in tags:
        t2 = t.strip()
        if not t2 or t2 in seen:
            continue
        cleaned.append(t2)
        seen.add(t2)

    device.tags = cleaned
    db.commit()
    db.refresh(device)
    return device

def add_device_tags(db: Session, device_id: int, tags: list[str]) -> Device | None:
    """Add tags to a device, preserving existing tags."""
    device = db.get(Device, device_id)
    if not device:
        return None

    existing = set(device.tags) if device.tags else set()
    for t in tags:
        t2 = t.strip()
        if not t2 or t2 in existing:
            continue
        existing.add(t2)

    device.tags = list(existing)
    db.commit()
    db.refresh(device)
    return device

def remove_device_tags(db: Session, device_id: int, tags: list[str]) -> Device | None:
    """Remove tags from a device, preserving other existing tags."""
    device = db.get(Device, device_id)
    if not device:
        return None

    if not device.tags:
        return device

    existing = set(device.tags)
    for t in tags:
        t2 = t.strip()
        if t2 in existing:
            existing.remove(t2)
    device.tags = sorted(existing)
    db.commit()
    db.refresh(device)
    return device