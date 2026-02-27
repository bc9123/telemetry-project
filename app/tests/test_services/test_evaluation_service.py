# tests/test_services/test_evaluation_service.py
import pytest
from datetime import datetime, timezone, timedelta
from app.services.evaluation_service import evaluate_rules_for_device
from app.db.models.telemetry_event import TelemetryEvent

class TestRuleEvaluation:
    """Test the core rule evaluation logic"""
    
    def test_simple_threshold_rule_fires(
        self,
        db_session,
        test_device,
        test_rule,
        create_telemetry_event
    ):
        """Test that a simple > threshold rule fires correctly"""
        # Arrange: Create events above threshold
        for i in range(5):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"temperature": 85.0},
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )

        # Act: Evaluate rules
        alert_ids = evaluate_rules_for_device(db_session, test_device.id)

        # Assert: Alert was created
        assert len(alert_ids) == 1

        # Verify alert details
        from app.db.models.alert import Alert
        alert = db_session.get(Alert, alert_ids[0])
        assert alert.device_id == test_device.id
        assert alert.rule_id == test_rule.id
        assert alert.details["evaluation"]["latest_value"] == 85.0
    
    def test_threshold_rule_does_not_fire_below_threshold(
        self,
        db_session,
        test_device,
        test_rule,
        create_telemetry_event
    ):
        """Test that rule doesn't fire when values are below threshold"""
        # Arrange: Create events below threshold
        for i in range(5):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"temperature": 75.0},  # Below 80.0
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
        
        # Act
        alert_ids = evaluate_rules_for_device(db_session, test_device.id)
        
        # Assert: No alerts
        assert len(alert_ids) == 0
    
    def test_k_of_n_rule_evaluation(
        self,
        db_session,
        test_device,
        test_rule,
        create_telemetry_event
    ):
        """Test k-of-n evaluation: 3 of last 5 must exceed threshold"""
        # Arrange: 3 above, 2 below
        values = [85.0, 75.0, 90.0, 70.0, 95.0]  # 3 above 80
        for i, val in enumerate(values):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"temperature": val},
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
        
        # Act
        alert_ids = evaluate_rules_for_device(db_session, test_device.id)

        # Assert: Alert fires (3 of 5 above threshold)
        assert len(alert_ids) == 1
    
    def test_k_of_n_rule_does_not_fire_when_insufficient(
        self,
        db_session,
        test_device,
        test_rule,
        create_telemetry_event
    ):
        """Test k-of-n doesn't fire with only 2 of 5"""
        # Arrange: Only 2 above threshold
        values = [85.0, 75.0, 70.0, 70.0, 90.0]  # Only 2 above 80
        for i, val in enumerate(values):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"temperature": val},
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
        
        # Act
        alert_ids = evaluate_rules_for_device(db_session, test_device.id)
        
        # Assert: No alert (only 2 of 5, need 3)
        assert len(alert_ids) == 0
    
    def test_cooldown_prevents_duplicate_alerts(
        self,
        db_session,
        test_device,
        test_rule,
        create_telemetry_event
    ):
        """Test that cooldown period prevents alert spam"""
        # Arrange: Create events that trigger rule
        for i in range(5):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"temperature": 85.0},
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
        
        # Act: First evaluation
        alert_ids_1 = evaluate_rules_for_device(db_session, test_device.id)
        assert len(alert_ids_1) == 1
        
        # Add more events (still above threshold)
        for i in range(5, 10):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"temperature": 85.0},
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
        
        # Act: Second evaluation (within cooldown)
        alert_ids_2 = evaluate_rules_for_device(db_session, test_device.id)
        
        # Assert: No new alerts (still in cooldown)
        assert len(alert_ids_2) == 0
    
    def test_tag_scoped_rule_applies_to_tagged_device(
        self,
        db_session,
        test_device,
        test_tag_rule,
        create_telemetry_event
    ):
        """Test that TAG-scoped rules only apply to devices with matching tag"""
        # Arrange: Device has "temperature" tag
        assert "temperature" in test_device.tags
        
        # Create events
        for i in range(3):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"cpu": 95.0},
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
        
        # Act
        alert_ids = evaluate_rules_for_device(db_session, test_device.id)
        
        # Assert: Alert fires (device has matching tag)
        assert len(alert_ids) == 1
    
    def test_tag_scoped_rule_does_not_apply_to_untagged_device(
        self,
        db_session,
        test_device,
        test_tag_rule,
        create_telemetry_event
    ):
        """Test TAG-scoped rule doesn't apply to devices without tag"""
        # Arrange: Remove tag from device
        test_device.tags = ["other-tag"]
        db_session.commit()
        
        # Create events
        for i in range(3):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"cpu": 95.0},
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
        
        # Act
        alert_ids = evaluate_rules_for_device(db_session, test_device.id)
        
        # Assert: No alert (device doesn't have matching tag)
        assert len(alert_ids) == 0
    
    def test_missing_metric_skips_evaluation(
        self,
        db_session,
        test_device,
        test_rule,
        create_telemetry_event
    ):
        """Test that events without the metric are skipped"""
        # Arrange: Create events with wrong metric
        for i in range(5):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"humidity": 50.0},  # Wrong metric
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
        
        # Act
        alert_ids = evaluate_rules_for_device(db_session, test_device.id)
        
        # Assert: No alerts (metric missing)
        assert len(alert_ids) == 0
    
    def test_insufficient_window_size_skips_rule(
        self,
        db_session,
        test_device,
        test_rule,
        create_telemetry_event
    ):
        """Test that rule doesn't evaluate with insufficient events"""
        # Arrange: Only 3 events, but rule needs 5
        for i in range(3):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"temperature": 85.0},
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
        
        # Act
        alert_ids = evaluate_rules_for_device(db_session, test_device.id)
        
        # Assert: No alerts (need 5 events, only have 3)
        assert len(alert_ids) == 0