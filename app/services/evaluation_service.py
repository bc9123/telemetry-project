# app/services/evaluation_service.py
from __future__ import annotations

import structlog

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, text

from app.db.models.device import Device
from app.db.models.alert import Alert
from app.db.models.telemetry_event import TelemetryEvent
from app.db.repositories.rule_repo import (
    list_enabled_rules_for_project,
    get_explicit_rule_ids_for_device,
)
from app.db.repositories.alert_repo import get_latest_alert_time, create_alert

logger = structlog.get_logger(__name__)

ALLOWED_OPS = {">", ">=", "<", "<="}

def _compare(op: str, value: float, threshold: float) -> bool:
    if op == ">":
        return value > threshold
    if op == ">=":
        return value >= threshold
    if op == "<":
        return value < threshold
    if op == "<=":
        return value <= threshold
    raise ValueError(f"Unsupported operator: {op}")


def evaluate_rules_for_device(db: Session, device_id: int) -> list[int]:
    """
    Evaluate all enabled project rules that apply to this device.
    Returns a list of created Alert IDs.
    """
    logger.info("evaluation_started", device_id=device_id)
    device = db.get(Device, device_id)
    if not device:
        logger.warning("device_not_found", device_id=device_id)
        return []

    rules = list_enabled_rules_for_project(db, project_id=device.project_id)
    logger.info("rules_loaded", device_id=device_id, project_id=device.project_id, rule_count=len(rules))
    
    if not rules:
        logger.info("no_rules", device_id=device_id)
        return []

    explicit_rule_ids = get_explicit_rule_ids_for_device(db, device_id=device_id)

    created_alert_ids: list[int] = []

    for rule in rules:
        # ---- applicability (ALL / EXPLICIT / TAG)
        if rule.scope == "ALL":
            applies = True
        elif rule.scope == "EXPLICIT":
            applies = rule.id in explicit_rule_ids
        elif rule.scope == "TAG":
            applies = bool(rule.tag) and (rule.tag in (device.tags or []))
        else:
            applies = False

        if not applies:
            continue

        # ---- validation
        if rule.operator not in ALLOWED_OPS:
            continue
        if rule.required_k > rule.window_n:
            continue

        # ---- load last N events
        q = (
            select(TelemetryEvent)
            .where(TelemetryEvent.device_id == device_id)
            .order_by(desc(TelemetryEvent.ts), desc(TelemetryEvent.id))
            .limit(rule.window_n)
        )
        events = list(db.execute(q).scalars().all())

        if len(events) < rule.window_n:
            continue

        # ---- evaluate (k-of-n)
        match_count = 0
        considered = 0

        latest_value: float | None = None
        latest_ts: datetime | None = None

        for ev in events:
            payload = ev.payload or {}
            raw = payload.get(rule.metric)

            if isinstance(raw, (int, float)):
                considered += 1

                # track "latest" numeric value based on event ordering (events are ts DESC)
                if latest_value is None:
                    latest_value = float(raw)
                    latest_ts = ev.ts

                if _compare(rule.operator, float(raw), float(rule.threshold)):
                    match_count += 1

        # If metric missing everywhere in window -> skip
        if considered == 0:
            continue

        if match_count < rule.required_k:
            continue

        # ---- Create alert with advisory lock protection ----
        # Use a separate function to handle the locked section cleanly
        alert_id = _try_create_alert_with_lock(
            db, device_id, rule, match_count, considered, latest_value, latest_ts
        )
        
        if alert_id is not None:
            logger.info(
                "alert_created",
                alert_id=alert_id,
                device_id=device_id,
                rule_id=rule.id,
                rule_name=rule.name,
                metric=rule.metric,
                threshold=rule.threshold,
                latest_value=latest_value
            )
            created_alert_ids.append(alert_id)
        else:
            logger.debug(
                "alert_skipped_cooldown",
                device_id=device_id,
                rule_id=rule.id
            )

    logger.info(
        "evaluation_completed",
        device_id=device_id,
        alerts_created=len(created_alert_ids)
    )
    
    return created_alert_ids


def _try_create_alert_with_lock(
    db: Session,
    device_id: int,
    rule,
    match_count: int,
    considered: int,
    latest_value: float | None,
    latest_ts: datetime | None,
) -> int | None:
    """
    Attempt to create an alert with advisory lock protection.
    Returns alert ID if created, None if skipped due to cooldown.
    
    This function commits its own transaction to ensure the advisory
    lock is held for the minimal necessary time.
    """
    try:
        # Acquire advisory lock (held until transaction commits/rolls back)
        # Convert device_id and rule_id to ensure they fit in int32 range for pg_advisory_xact_lock
        db.execute(
            text("SELECT pg_advisory_xact_lock(:device_id, :rule_id)"),
            {"device_id": device_id, "rule_id": rule.id}
        )

        # Check cooldown AFTER acquiring lock
        last_ts_alert = get_latest_alert_time(db, device_id=device_id, rule_id=rule.id)
        now = datetime.now(timezone.utc)
        
        if last_ts_alert and (now - last_ts_alert) < timedelta(seconds=rule.cooldown_seconds):
            # Still in cooldown, rollback and return None
            db.rollback()
            return None

        # Not in cooldown, create the alert
        details = {
            "rule": {
                "id": rule.id,
                "name": rule.name,
                "metric": rule.metric,
                "operator": rule.operator,
                "threshold": rule.threshold,
                "window_n": rule.window_n,
                "required_k": rule.required_k,
                "cooldown_seconds": rule.cooldown_seconds,
                "scope": rule.scope,
                "tag": getattr(rule, "tag", None),
            },
            "evaluation": {
                "device_id": device_id,
                "match_count": match_count,
                "considered": considered,
                "latest_value": latest_value,
                "latest_ts": latest_ts.isoformat() if latest_ts else None,
            },
        }

        alert = Alert(device_id=device_id, rule_id=rule.id, details=details)
        db.add(alert)
        db.commit()  # Commit releases the advisory lock
        db.refresh(alert)  # Get the alert ID
        
        return alert.id

    except Exception as e:
        db.rollback()
        raise e