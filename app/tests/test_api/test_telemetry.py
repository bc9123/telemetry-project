# tests/test_api/test_telemetry.py
import pytest
from datetime import datetime, timezone

class TestTelemetryIngestion:
    """Test the telemetry ingestion API endpoint"""
    
    def test_ingest_telemetry_success(
        self,
        client,
        test_api_key,
        test_device,
        mocker
    ):
        """Test successful telemetry ingestion"""
        # Mock the Celery task
        mock_delay = mocker.patch("app.api.routes.telemetry.ingest_events.delay")
        
        # Arrange
        payload = {
            "device_external_id": test_device.external_id,
            "events": [
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "data": {"temperature": 75.0}
                }
            ]
        }
        
        # Act
        response = client.post(
            "/telemetry",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        # Assert
        assert response.status_code == 202
        data = response.json()
        assert data["queued"] == 1
        assert data["device_id"] == test_device.id
        
        # Verify Celery task was called
        mock_delay.assert_called_once()
    
    def test_ingest_requires_api_key(self, client):
        """Test that ingestion requires API key"""
        payload = {
            "device_external_id": "test-device",
            "events": [{"ts": datetime.now(timezone.utc).isoformat(), "data": {}}]
        }
        
        response = client.post("/telemetry", json=payload)
        
        assert response.status_code == 401
    
    def test_ingest_rejects_invalid_api_key(self, client):
        """Test that invalid API keys are rejected"""
        payload = {
            "device_external_id": "test-device",
            "events": [{"ts": datetime.now(timezone.utc).isoformat(), "data": {}}]
        }
        
        response = client.post(
            "/telemetry",
            json=payload,
            headers={"X-API-Key": "invalid.key"}
        )
        
        assert response.status_code == 403
    
    def test_ingest_rejects_empty_events(
        self,
        client,
        test_api_key
    ):
        """Test that empty event list is rejected"""
        payload = {
            "device_external_id": "test-device",
            "events": []
        }
        
        response = client.post(
            "/telemetry",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]
    
    def test_ingest_rejects_too_many_events(
        self,
        client,
        test_api_key
    ):
        """Test that batches over 5000 events are rejected"""
        payload = {
            "device_external_id": "test-device",
            "events": [
                {"ts": datetime.now(timezone.utc).isoformat(), "data": {}}
                for _ in range(5001)
            ]
        }
        
        response = client.post(
            "/telemetry",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 400
        assert "too many events" in response.json()["detail"]
    
    def test_ingest_rejects_unknown_device(
        self,
        client,
        test_api_key
    ):
        """Test that unknown device external_id is rejected"""
        payload = {
            "device_external_id": "non-existent-device",
            "events": [{"ts": datetime.now(timezone.utc).isoformat(), "data": {}}]
        }
        
        response = client.post(
            "/telemetry",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 404
        assert "device not found" in response.json()["detail"]