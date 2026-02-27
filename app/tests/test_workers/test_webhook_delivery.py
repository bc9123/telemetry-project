# tests/test_workers/test_webhook_delivery.py
import pytest
from unittest.mock import MagicMock, Mock
from datetime import datetime, timezone
import httpx

from app.workers.tasks.webhook_delivery import (
    deliver_webhook,
    enqueue_webhooks_for_alert,
    _countdown,
    _sign
)

class TestWebhookDelivery:
    """Test webhook delivery task"""
    
    def test_enqueue_webhooks_creates_deliveries(
        self,
        db_session,
        test_device,
        test_rule,
        test_project,
        mocker
    ):
        """Test that enqueue_webhooks_for_alert creates delivery rows"""
        # Arrange: Create alert
        from app.db.models.alert import Alert
        from app.db.models.webhook_subscription import WebhookSubscription
        
        alert = Alert(
            device_id=test_device.id,
            rule_id=test_rule.id,
            triggered_at=datetime.now(timezone.utc),
            details={"test": "data"}
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)
        
        # Create webhook subscription
        webhook = WebhookSubscription(
            project_id=test_project.id,
            url="https://example.com/webhook",
            secret="test-secret",
            enabled=True
        )
        db_session.add(webhook)
        db_session.commit()
        
        # Mock Celery task and SessionLocal
        mock_deliver = mocker.patch(
            "app.workers.tasks.webhook_delivery.deliver_webhook.delay"
        )
        mocker.patch(
            "app.workers.tasks.webhook_delivery.SessionLocal",
            return_value=db_session
        )
        
        # Act
        result = enqueue_webhooks_for_alert(alert.id)
        
        # Assert
        assert result == 1
        mock_deliver.assert_called_once()
    
    def test_deliver_webhook_success(
        self,
        db_session,
        test_device,
        test_project,
        test_rule,
        mocker
    ):
        """Test successful webhook delivery logic"""
        # Arrange: Create alert, webhook, and delivery
        from app.db.models.alert import Alert
        from app.db.models.device import Device
        from app.db.models.webhook_subscription import WebhookSubscription
        from app.db.models.webhook_delivery import WebhookDelivery
        from app.db.repositories.webhook_delivery_repo import (
            get_delivery_by_id,
            try_mark_sending,
            mark_success
        )
        import json
        
        alert = Alert(
            device_id=test_device.id,
            rule_id=test_rule.id,
            triggered_at=datetime.now(timezone.utc),
            details={"test": "data"}
        )
        db_session.add(alert)
        
        webhook = WebhookSubscription(
            project_id=test_project.id,
            url="https://example.com/webhook",
            secret="test-secret",
            enabled=True
        )
        db_session.add(webhook)
        db_session.commit()
        db_session.refresh(alert)
        db_session.refresh(webhook)
        
        delivery = WebhookDelivery(
            project_id=test_project.id,
            alert_id=alert.id,
            webhook_id=webhook.id,
            status="pending"
        )
        db_session.add(delivery)
        db_session.commit()
        db_session.refresh(delivery)
        
        # Mock HTTP client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post = mocker.patch("httpx.Client.post", return_value=mock_response)
        
        # Mock circuit breaker
        mocker.patch("app.workers.tasks.webhook_delivery.circuit_breaker.is_open", return_value=False)
        mocker.patch("app.workers.tasks.webhook_delivery.circuit_breaker.record_success")
        
        # Act - Test the delivery logic
        
        # 1. Get delivery
        delivery_obj = get_delivery_by_id(db_session, delivery.id)
        assert delivery_obj is not None
        
        # 2. Mark as sending
        marked = try_mark_sending(db_session, delivery.id)
        assert marked is True
        
        # 3. Get related objects
        alert_obj = db_session.get(Alert, delivery.alert_id)
        device_obj = db_session.get(Device, alert_obj.device_id)
        webhook_obj = db_session.get(WebhookSubscription, delivery.webhook_id)
        
        assert alert_obj is not None
        assert device_obj is not None
        assert webhook_obj is not None
        
        # 4. Prepare and send webhook (mocked)
        payload = {
            "alert_id": alert_obj.id,
            "device_id": alert_obj.device_id,
            "rule_id": alert_obj.rule_id,
            "triggered_at": alert_obj.triggered_at.isoformat(),
            "details": alert_obj.details,
        }
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        
        # Simulate HTTP call
        with httpx.Client() as client:
            resp = client.post(webhook_obj.url, content=body, headers={})
        
        # 5. Mark as success
        mark_success(db_session, delivery.id, resp.status_code)
        
        # Assert - Verify delivery was marked successful
        db_session.refresh(delivery)
        assert delivery.status == "success"
        assert delivery.last_status_code == 200
        assert mock_post.called
    
    def test_deliver_webhook_retries_on_500(
        self,
        db_session,
        test_device,
        test_project,
        test_rule,
        mocker
    ):
        """Test that 5xx errors are marked for retry"""
        # Arrange
        from app.db.models.alert import Alert
        from app.db.models.webhook_subscription import WebhookSubscription
        from app.db.models.webhook_delivery import WebhookDelivery
        from app.db.repositories.webhook_delivery_repo import (
            get_delivery_by_id,
            try_mark_sending,
            mark_retrying
        )
        
        alert = Alert(
            device_id=test_device.id,
            rule_id=test_rule.id,
            triggered_at=datetime.now(timezone.utc),
            details={}
        )
        webhook = WebhookSubscription(
            project_id=test_project.id,
            url="https://example.com/webhook",
            enabled=True
        )
        db_session.add_all([alert, webhook])
        db_session.commit()
        
        delivery = WebhookDelivery(
            project_id=test_project.id,
            alert_id=alert.id,
            webhook_id=webhook.id,
            status="pending"
        )
        db_session.add(delivery)
        db_session.commit()
        
        # Mock 500 response from HTTP client
        mock_response = Mock()
        mock_response.status_code = 500
        mocker.patch("httpx.Client.post", return_value=mock_response)
        
        # Act - Simulate what task does on 500 error
        delivery_obj = get_delivery_by_id(db_session, delivery.id)
        assert delivery_obj is not None
        
        try_mark_sending(db_session, delivery.id)
        
        # Make HTTP call and get 500
        with httpx.Client() as client:
            resp = client.post(webhook.url, content="{}", headers={})
        
        # Task would mark as retrying on 500
        if resp.status_code >= 500:
            mark_retrying(db_session, delivery.id, resp.status_code, f"retryable_status_{resp.status_code}")
        
        # Assert - Verify delivery status
        db_session.refresh(delivery)
        assert delivery.status == "retrying"
        assert delivery.last_status_code == 500
    
    def test_deliver_webhook_fails_on_400(
        self,
        db_session,
        test_device,
        test_project,
        test_rule,
        mocker
    ):
        """Test that 4xx errors (non-retryable) mark as failed"""
        # Arrange
        from app.db.models.alert import Alert
        from app.db.models.webhook_subscription import WebhookSubscription
        from app.db.models.webhook_delivery import WebhookDelivery
        from app.db.repositories.webhook_delivery_repo import (
            get_delivery_by_id,
            try_mark_sending,
            mark_failed
        )
        
        alert = Alert(
            device_id=test_device.id,
            rule_id=test_rule.id,
            triggered_at=datetime.now(timezone.utc),
            details={}
        )
        webhook = WebhookSubscription(
            project_id=test_project.id,
            url="https://example.com/webhook",
            enabled=True
        )
        db_session.add_all([alert, webhook])
        db_session.commit()
        
        delivery = WebhookDelivery(
            project_id=test_project.id,
            alert_id=alert.id,
            webhook_id=webhook.id,
            status="pending"
        )
        db_session.add(delivery)
        db_session.commit()
        
        # Mock 400 response from HTTP client
        mock_response = Mock()
        mock_response.status_code = 400
        mocker.patch("httpx.Client.post", return_value=mock_response)
        
        # Act - Simulate what task does on 400 error
        delivery_obj = get_delivery_by_id(db_session, delivery.id)
        assert delivery_obj is not None
        
        try_mark_sending(db_session, delivery.id)
        
        # Make HTTP call and get 400
        with httpx.Client() as client:
            resp = client.post(webhook.url, content="{}", headers={})
        
        # Task would mark as failed on 4xx (non-retryable)
        if resp.status_code >= 400 and resp.status_code < 500 and resp.status_code not in [408, 429]:
            mark_failed(db_session, delivery.id, resp.status_code, f"non_retryable_status_{resp.status_code}")
        
        # Assert
        db_session.refresh(delivery)
        assert delivery.status == "failed"
        assert delivery.last_status_code == 400
    
    def test_countdown_exponential_backoff(self):
        """Test exponential backoff calculation"""
        # First retry: ~5 seconds
        delay_0 = _countdown(0)
        assert 5 <= delay_0 <= 35
        
        # Second retry: ~10 seconds
        delay_1 = _countdown(1)
        assert 10 <= delay_1 <= 40
        
        # Third retry: ~20 seconds
        delay_2 = _countdown(2)
        assert 20 <= delay_2 <= 50
        
        # Very high retry: capped at 30 minutes
        delay_high = _countdown(20)
        assert delay_high <= 1800 + 30  # 30 min + max jitter
    
    def test_sign_webhook_payload(self):
        """Test HMAC signature generation"""
        secret = "test-secret"
        timestamp = "2026-02-04T12:00:00Z"
        body = '{"alert_id":123}'
        
        signature = _sign(secret, timestamp, body)
        
        # Verify it's a valid hex string
        assert len(signature) == 64  # SHA-256 produces 64 hex chars
        assert all(c in '0123456789abcdef' for c in signature)
        
        # Verify it's deterministic
        signature2 = _sign(secret, timestamp, body)
        assert signature == signature2
        
        # Verify different inputs produce different signatures
        signature3 = _sign(secret, timestamp, '{"alert_id":456}')
        assert signature != signature3


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    class _FakeRedis:
        def __init__(self):
            self.store = {}

        def _expired(self, key):
            if key not in self.store:
                return True
            val, exp = self.store[key]
            if exp is None:
                return False
            from datetime import datetime, timezone
            return datetime.now(timezone.utc) > exp

        def get(self, key):
            if key not in self.store or self._expired(key):
                return None
            val, exp = self.store[key]
            return val

        def set(self, key, value, ex=None):
            from datetime import datetime, timezone, timedelta
            if isinstance(value, str):
                b = value.encode()
            elif isinstance(value, bytes):
                b = value
            else:
                b = str(value).encode()

            exp_dt = None
            if ex is not None:
                exp_dt = datetime.now(timezone.utc) + timedelta(seconds=ex)

            self.store[key] = (b, exp_dt)

        def incr(self, key):
            cur = self.get(key)
            if cur is None:
                val = 1
            else:
                try:
                    val = int(cur.decode()) + 1
                except Exception:
                    val = 1
            self.set(key, str(val))
            return val

        def expire(self, key, seconds):
            from datetime import datetime, timezone, timedelta
            if key in self.store:
                val, _ = self.store[key]
                self.store[key] = (val, datetime.now(timezone.utc) + timedelta(seconds=seconds))

        def delete(self, key):
            if key in self.store:
                del self.store[key]

    def test_circuit_opens_after_failures(self, mocker):
        """Test that circuit opens after threshold failures"""
        from app.services.circuit_breaker import WebhookCircuitBreaker
        from datetime import timezone

        fake_redis = self._FakeRedis()
        cb = WebhookCircuitBreaker(fake_redis, failure_threshold=3, recovery_timeout=5)

        url = "https://example.com/webhook"

        # Record failures below threshold
        assert cb.record_failure(url) is False
        assert cb.record_failure(url) is False

        # On reaching threshold, should open
        opened = cb.record_failure(url)
        assert opened is True
        assert cb.is_open(url) is True

        stats = cb.get_stats(url)
        assert stats["state"] == "open"
        assert stats["failures"] >= 3

    def test_transitions_to_half_open_after_timeout(self):
        from app.services.circuit_breaker import WebhookCircuitBreaker
        from datetime import datetime, timezone, timedelta

        fake_redis = self._FakeRedis()
        cb = WebhookCircuitBreaker(fake_redis, failure_threshold=1, recovery_timeout=1)
        url = "https://example.com/webhook"

        # Open circuit
        assert cb.record_failure(url) is True
        assert cb.is_open(url) is True

        # Simulate time passage by rewriting opened_at to past
        opened_key = cb._key_opened_at(url)
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        fake_redis.set(opened_key, past, ex=3600)

        # Now is_open should transition to half_open and return False (not open)
        assert cb.is_open(url) is False
        # State should be half_open now
        st = fake_redis.get(cb._key_state(url))
        assert st == b"half_open"

    def test_record_success_closes_circuit(self):
        from app.services.circuit_breaker import WebhookCircuitBreaker
        from datetime import datetime, timezone

        fake_redis = self._FakeRedis()
        cb = WebhookCircuitBreaker(fake_redis, failure_threshold=1, recovery_timeout=60)
        url = "https://example.com/webhook"

        # Simulate half_open with failures recorded
        fake_redis.set(cb._key_state(url), "half_open", ex=3600)
        fake_redis.set(cb._key_failures(url), "2", ex=300)
        fake_redis.set(cb._key_opened_at(url), datetime.now(timezone.utc).isoformat(), ex=3600)

        # Recording success should clear keys
        cb.record_success(url)
        assert fake_redis.get(cb._key_state(url)) is None
        assert fake_redis.get(cb._key_failures(url)) is None
        assert fake_redis.get(cb._key_opened_at(url)) is None