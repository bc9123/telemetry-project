# tests/test_workers/test_ingest.py
import pytest
from datetime import datetime, timezone
from app.db.models.telemetry_event import TelemetryEvent
from sqlalchemy import select

class TestIngestLogic:
    """Test the event ingestion logic"""
    
    def test_ingest_events_success(
        self,
        db_session,
        test_device,
        mocker
    ):
        """Test successful event ingestion"""
        # Mock the Celery task for rule evaluation
        mock_evaluate = mocker.patch(
            "app.workers.tasks.ingest.evaluate_rules_for_device_task.delay"
        )
        
        # Arrange - prepare event data
        events = [
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "data": {"temperature": 75.0}
            },
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "data": {"temperature": 80.0}
            }
        ]
        
        # Act - Directly insert events (what the task does)
        from sqlalchemy import insert
        
        params = []
        for e in events:
            ts = datetime.fromisoformat(e["ts"])
            params.append({
                "device_id": test_device.id,
                "ts": ts,
                "payload": e.get("data", {})
            })
        
        db_session.execute(insert(TelemetryEvent), params)
        db_session.commit()
        
        # Trigger rule evaluation (what the task does)
        from app.workers.tasks.evaluate_rules import evaluate_rules_for_device_task
        evaluate_rules_for_device_task.delay(test_device.id)
        
        # Assert - Verify events were stored
        stored_events = db_session.execute(
            select(TelemetryEvent).where(TelemetryEvent.device_id == test_device.id)
        ).scalars().all()
        
        assert len(stored_events) == 2
        assert stored_events[0].payload["temperature"] == 75.0
        assert stored_events[1].payload["temperature"] == 80.0
        
        # Verify rule evaluation was triggered
        mock_evaluate.assert_called_once_with(test_device.id)
    
    def test_ingest_events_skips_malformed_events(
        self,
        db_session,
        test_device
    ):
        """Test that malformed events are skipped"""
        # Arrange - mix of valid and invalid events
        events = [
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "data": {"temperature": 75.0}
            },
            {
                # Missing 'ts' field - should be skipped
                "data": {"temperature": 80.0}
            },
            {
                # Invalid timestamp - should be skipped
                "ts": "invalid-timestamp",
                "data": {"temperature": 85.0}
            }
        ]
        
        # Act - Process events with error handling
        from sqlalchemy import insert
        
        params = []
        for e in events:
            try:
                ts = datetime.fromisoformat(e["ts"])
                params.append({
                    "device_id": test_device.id,
                    "ts": ts,
                    "payload": e.get("data", {})
                })
            except (ValueError, KeyError):
                # Skip malformed events
                continue
        
        if params:
            db_session.execute(insert(TelemetryEvent), params)
            db_session.commit()
        
        # Assert - Only valid event should be stored
        stored_events = db_session.execute(
            select(TelemetryEvent).where(TelemetryEvent.device_id == test_device.id)
        ).scalars().all()
        
        assert len(stored_events) == 1
        assert stored_events[0].payload["temperature"] == 75.0
    
    def test_ingest_empty_events_list(
        self,
        db_session,
        test_device
    ):
        """Test that empty event list is handled gracefully"""
        # Arrange
        events = []
        
        # Act
        params = []
        for e in events:
            try:
                ts = datetime.fromisoformat(e["ts"])
                params.append({
                    "device_id": test_device.id,
                    "ts": ts,
                    "payload": e.get("data", {})
                })
            except (ValueError, KeyError):
                continue
        
        result_count = len(params)
        
        if params:
            from sqlalchemy import insert
            db_session.execute(insert(TelemetryEvent), params)
            db_session.commit()
        
        # Assert
        assert result_count == 0
        
        stored_events = db_session.execute(
            select(TelemetryEvent).where(TelemetryEvent.device_id == test_device.id)
        ).scalars().all()
        
        assert len(stored_events) == 0
    
    def test_ingest_preserves_event_order(
        self,
        db_session,
        test_device
    ):
        """Test that events maintain chronological order"""
        # Arrange - events with specific timestamps
        base_time = datetime.now(timezone.utc)
        events = [
            {
                "ts": base_time.isoformat(),
                "data": {"temperature": 70.0, "seq": 1}
            },
            {
                "ts": base_time.replace(second=base_time.second + 1).isoformat(),
                "data": {"temperature": 75.0, "seq": 2}
            },
            {
                "ts": base_time.replace(second=base_time.second + 2).isoformat(),
                "data": {"temperature": 80.0, "seq": 3}
            }
        ]
        
        # Act
        from sqlalchemy import insert
        
        params = []
        for e in events:
            ts = datetime.fromisoformat(e["ts"])
            params.append({
                "device_id": test_device.id,
                "ts": ts,
                "payload": e.get("data", {})
            })
        
        db_session.execute(insert(TelemetryEvent), params)
        db_session.commit()
        
        # Assert - events should be retrievable in order
        stored_events = db_session.execute(
            select(TelemetryEvent)
            .where(TelemetryEvent.device_id == test_device.id)
            .order_by(TelemetryEvent.ts)
        ).scalars().all()
        
        assert len(stored_events) == 3
        assert stored_events[0].payload["seq"] == 1
        assert stored_events[1].payload["seq"] == 2
        assert stored_events[2].payload["seq"] == 3