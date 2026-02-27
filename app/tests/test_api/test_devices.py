# tests/test_api/test_devices.py
import pytest

class TestDeviceCRUD:
    """Test device CRUD operations"""
    
    def test_create_device(
        self,
        client,
        test_api_key,
        test_project
    ):
        """Test creating a new device"""
        payload = {
            "external_id": "new-device-001",
            "name": "New Test Device",
            "tags": ["production", "sensor"]
        }
        
        response = client.post(
            f"/projects/{test_project.id}/devices",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["external_id"] == "new-device-001"
        assert data["name"] == "New Test Device"
        assert "production" in data["tags"]
    
    def test_get_device(
        self,
        client,
        test_api_key,
        test_device
    ):
        """Test retrieving a device"""
        response = client.get(
            f"/projects/{test_device.project_id}/devices/{test_device.id}",
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_device.id
        assert data["external_id"] == test_device.external_id
    
    def test_list_devices(
        self,
        client,
        test_api_key,
        test_project,
        test_device
    ):
        """Test listing devices for a project"""
        response = client.get(
            f"/projects/{test_project.id}/devices",
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(d["id"] == test_device.id for d in data)
    
    def test_update_device_tags(
        self,
        client,
        test_api_key,
        test_device,
        db_session
    ):
        """Test updating device tags"""
        payload = {
            "tags": ["updated", "new-tag"]
        }
        
        response = client.patch(
            f"/projects/{test_device.project_id}/devices/{test_device.id}/tags",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "updated" in data["tags"]
        assert "new-tag" in data["tags"]
    
    def test_delete_device(
        self,
        client,
        test_api_key,
        test_device
    ):
        """Test deleting a device"""
        response = client.delete(
            f"/projects/{test_device.project_id}/devices/{test_device.id}",
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 204
        
        get_response = client.get(
            f"/projects/{test_device.project_id}/devices/{test_device.id}",
            headers={"X-API-Key": test_api_key.raw_key}
        )
        assert get_response.status_code == 404
    
    def test_duplicate_external_id_rejected(
        self,
        client,
        test_api_key,
        test_project,
        test_device
    ):
        """Test that duplicate external_id in same project is rejected"""
        payload = {
            "external_id": test_device.external_id,
            "name": "Duplicate Device"
        }
        
        response = client.post(
            f"/projects/{test_project.id}/devices",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 400