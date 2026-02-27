# app/db/repositories/rule_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.db.models.rule import Rule
from app.db.models.rule_device import RuleDevice
from app.schemas.rule import RuleUpdate

def create_rule(db: Session, rule: Rule) -> Rule:
    """Create a new rule."""
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

def list_rules_for_project(db: Session, project_id: int) -> list[Rule]:
    """List all rules for a given project"""
    q = select(Rule).where(Rule.project_id == project_id).order_by(Rule.id.desc())
    return list(db.execute(q).scalars().all())

def get_rule(db: Session, rule_id: int) -> Rule | None:
    """Get a rule by its ID."""
    return db.get(Rule, rule_id)

def list_enabled_rules_for_project(db: Session, project_id: int) -> list[Rule]:
    """List all enabled rules for a given project."""
    q = select(Rule).where(Rule.project_id == project_id, Rule.enabled.is_(True))
    return list(db.execute(q).scalars().all())

def update_rule(db: Session, rule_id: int, rule_update: RuleUpdate) -> Rule | None:
    """Update an existing rule with new data."""
    existing_rule = db.get(Rule, rule_id)
    if not existing_rule:
        return None

    update_data = rule_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_rule, field, value)

    db.commit()
    db.refresh(existing_rule)
    return existing_rule

def delete_rule(db: Session, rule_id: int) -> bool:
    """Delete a rule by its ID."""
    rule = db.get(Rule, rule_id)
    if not rule:
        return False
    db.delete(rule)
    db.commit()
    return True

def get_explicit_rule_ids_for_device(db: Session, device_id: int) -> set[int]:
    """Get the set of rule IDs that are explicitly associated with a given device."""
    q = select(RuleDevice.rule_id).where(RuleDevice.device_id == device_id)
    return set(db.execute(q).scalars().all())

def replace_rule_devices(db: Session, rule_id: int, device_ids: list[int]) -> None:
    """Replace the list of devices associated with a rule."""
    db.execute(delete(RuleDevice).where(RuleDevice.rule_id == rule_id))
    for did in device_ids:
        db.add(RuleDevice(rule_id=rule_id, device_id=did))
    db.commit()
