# app/services/rule_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.rule import Rule
from app.db.repositories.rule_repo import create_rule, delete_rule, list_enabled_rules_for_project, list_rules_for_project, get_rule, replace_rule_devices, update_rule
from app.db.repositories.device_repo import list_device_ids_for_project, get_device

def create_rule_service(db: Session, project_id: int, data) -> Rule:
    """Create a new rule within a specific project."""
    if data.required_k > data.window_n:
        raise HTTPException(status_code=400, detail="required_k cannot be greater than window_n")
    
    rule = Rule(
        project_id=project_id,
        name=data.name,
        metric=data.metric,
        operator=data.operator,
        threshold=data.threshold,
        window_n=data.window_n,
        required_k=data.required_k,
        cooldown_seconds=data.cooldown_seconds,
        enabled=data.enabled,
        scope=data.scope,
        tag=data.tag,
    )
    return create_rule(db, rule)

def list_rules_service(db: Session, project_id: int) -> list[Rule]:
    """List all rules for a specific project."""
    return list_rules_for_project(db, project_id)

def get_rule_service(db: Session, rule_id: int) -> Rule:
    """Get a specific rule by its ID."""
    rule = get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    return rule

def list_enabled_rules_for_project_service(db: Session, project_id: int) -> list[Rule]:
    """List all enabled rules for a specific project."""
    return list_enabled_rules_for_project(db, project_id)

def update_rule_service(db: Session, rule_id: int, data) -> Rule:
    """Update an existing rule."""
    if data.required_k is not None and data.window_n is not None and data.required_k > data.window_n:
        raise HTTPException(status_code=400, detail="required_k cannot be greater than window_n")
    updated_rule = update_rule(db, rule_id, data)
    return updated_rule

def delete_rule_service(db: Session, rule_id: int) -> None:
    """Delete a specific rule by its ID."""
    if not delete_rule(db, rule_id):
        raise HTTPException(status_code=404, detail="rule not found")

def assign_rule_devices_service(db: Session, rule_id: int, device_ids: list[int]) -> None:
    """Assign a list of devices to a specific rule."""
    rule = get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")

    for did in device_ids:
        dev = get_device(db, did)
        if not dev:
            raise HTTPException(status_code=404, detail=f"device not found: {did}")
        if dev.project_id != rule.project_id:
            raise HTTPException(status_code=400, detail=f"device {did} not in rule's project")

    replace_rule_devices(db, rule_id=rule_id, device_ids=device_ids)
