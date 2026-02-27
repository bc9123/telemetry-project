# tests/test_integration/test_alert_flow.py
from datetime import datetime, timezone, timedelta

class TestAlertFlow:
    """Test the complete flow: ingest → evaluate → alert → webhook"""
    
    def test_complete_alert_flow(
        self,
        db_session,
        test_device,
        test_rule,
        test_project,
        create_telemetry_event,
        mocker
    ):
        """Test complete flow from ingestion to alert creation"""
        # Arrange: Create webhook subscription
        from app.db.models.webhook_subscription import WebhookSubscription
        
        webhook = WebhookSubscription(
            project_id=test_project.id,
            url="https://example.com/webhook",
            secret="test-secret",
            enabled=True
        )
        db_session.add(webhook)
        db_session.commit()
        
        # Mock webhook delivery task
        mock_deliver = mocker.patch(
            "app.workers.tasks.webhook_delivery.enqueue_webhooks_for_alert.delay"
        )
        
        # Act: Create telemetry events that trigger the rule
        # (5 events with temperature=85.0, which exceeds threshold of 80.0)
        for i in range(5):
            create_telemetry_event(
                device_id=test_device.id,
                payload={"temperature": 85.0},
                ts=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
        
        # Evaluate rules using the service (business logic)
        from app.services.evaluation_service import evaluate_rules_for_device
        alert_ids = evaluate_rules_for_device(db_session, test_device.id)
        
        # Simulate what the Celery task does: enqueue webhooks for each alert
        for aid in alert_ids:
            from app.workers.tasks.webhook_delivery import enqueue_webhooks_for_alert
            enqueue_webhooks_for_alert.delay(aid)
        
        # Assert: Alert was created
        assert len(alert_ids) == 1, "Expected exactly 1 alert to be created"
        
        # Verify webhook was enqueued
        mock_deliver.assert_called_once_with(alert_ids[0])
        
        # Verify alert details
        from app.db.models.alert import Alert
        alert = db_session.get(Alert, alert_ids[0])
        assert alert is not None, "Alert should exist in database"
        assert alert.device_id == test_device.id
        assert alert.rule_id == test_rule.id
        assert alert.details["rule"]["name"] == test_rule.name
        assert alert.details["evaluation"]["latest_value"] == 85.0
        
        # Verify the alert is associated with correct webhook subscription
        from app.db.repositories.webhook_repo import list_webhooks
        webhooks = list_webhooks(db_session, project_id=test_project.id, enabled_only=True)
        assert len(webhooks) == 1
        assert webhooks[0].id == webhook.id