from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.telemetry_event import TelemetryEvent
from app.workers.tasks.evaluate_rules import evaluate_rules_for_device_task

import structlog

logger = structlog.get_logger(__name__)

@celery_app.task(name="app.workers.tasks.ingest_events")
def ingest_events(device_id: int, events: list[dict]):
    """
    Ingest telemetry events for a specific device. Each event should be a dict with at least a "ts" key (ISO 8601 timestamp) and optionally a "data" key (dict of event payload).
    events: [{"ts": "2026-01-09T12:00:00+00:00", "data": {...}}, ...]
    """
    
    logger.info(
        "task_started",
        task="ingest_events",
        device_id=device_id,
        event_count=len(events)
    )
    
    if not events:
        logger.warning("empty_events", device_id=device_id)
        return 0

    db: Session = SessionLocal()
    try:
        params = []
        for e in events:
            try:
                ts = datetime.fromisoformat(e["ts"])
                params.append({
                    "device_id": device_id,
                    "ts": ts,
                    "payload": e.get("data", {})
                })
            except (ValueError, KeyError) as err:
                logger.warning(
                    "skipping_malformed_event",
                    device_id=device_id,
                    error=str(err)
                )
                continue

        if not params:
            logger.warning("no_valid_events", device_id=device_id)
            return 0

        db.execute(insert(TelemetryEvent), params)
        db.commit()
        
        logger.info(
            "events_ingested",
            device_id=device_id,
            event_count=len(events)
        )
        
        evaluate_rules_for_device_task.delay(device_id)
        return len(params)
        
    except Exception as e:
        logger.exception("ingest_events_failed", device_id=device_id)
        db.rollback()
        raise
        
    finally:
        db.close()
        logger.info("task_finished", task="ingest_events", device_id=device_id)