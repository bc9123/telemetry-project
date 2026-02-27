# app/api/routes/rules.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.rate_limits import RateLimits, limiter
from app.schemas.rule import RuleCreate, RuleOut, RuleAssignDevices, RuleUpdate
from app.services.rule_service import create_rule_service, delete_rule_service, get_rule_service, list_enabled_rules_for_project_service, list_rules_service, assign_rule_devices_service, update_rule_service

router = APIRouter(tags=["rules"])

@router.post("/projects/{project_id}/rules", response_model=RuleOut, status_code=201)
@limiter.limit(RateLimits.RULE_CREATE)
def create_rule(request: Request, project_id: int, payload: RuleCreate, db: Session = Depends(get_db)):
    """Create a new rule within the specified project"""
    return create_rule_service(db, project_id=project_id, data=payload)

@router.get("/projects/{project_id}/rules", response_model=list[RuleOut])
def list_rules(project_id: int, db: Session = Depends(get_db)):
    """List all rules for a specific project"""
    return list_rules_service(db, project_id=project_id)

@router.get("/rules/{rule_id}", response_model=RuleOut)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get details of a specific rule by its ID"""
    return get_rule_service(db, rule_id=rule_id)

@router.get("/projects/{project_id}/rules/enabled", response_model=list[RuleOut])
def list_enabled_rules_for_project(project_id: int, db: Session = Depends(get_db)):
    """List all enabled rules for a specific project"""
    return list_enabled_rules_for_project_service(db, project_id=project_id)

@router.patch("/rules/{rule_id}", response_model=RuleOut)
@limiter.limit(RateLimits.RULE_CREATE)
def update_rule(request: Request, rule_id: int, payload: RuleUpdate, db: Session = Depends(get_db)):
    """Update an existing rule by its ID"""
    return update_rule_service(db, rule_id=rule_id, data=payload)

@router.delete("/rules/{rule_id}", status_code=204)
@limiter.limit(RateLimits.RULE_CREATE)
def delete_rule(request: Request, rule_id: int, db: Session = Depends(get_db)):
    """Delete a specific rule by its ID"""
    delete_rule_service(db, rule_id=rule_id)
    return None

@router.post("/rules/{rule_id}/devices", status_code=204)
@limiter.limit(RateLimits.RULE_ASSIGN_DEVICES)
def assign_rule_devices(request: Request, rule_id: int, payload: RuleAssignDevices, db: Session = Depends(get_db)):
    """Assign a list of devices to a specific rule"""
    assign_rule_devices_service(db, rule_id=rule_id, device_ids=payload.device_ids)
    return None
