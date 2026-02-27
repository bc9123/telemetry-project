# tests/test_api/test_rules.py
import pytest

class TestRuleCRUD:
    """Test rule CRUD operations"""
    
    def test_create_rule(
        self,
        client,
        test_api_key,
        test_project
    ):
        """Test creating a new rule"""
        payload = {
            "name": "CPU Alert",
            "metric": "cpu",
            "operator": ">",
            "threshold": 90.0,
            "window_n": 5,
            "required_k": 3,
            "cooldown_seconds": 300,
            "scope": "ALL",
            "enabled": True
        }
        
        response = client.post(
            f"/projects/{test_project.id}/rules",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "CPU Alert"
        assert data["metric"] == "cpu"
        assert data["threshold"] == 90.0
    
    def test_create_tag_scoped_rule(
        self,
        client,
        test_api_key,
        test_project
    ):
        """Test creating a TAG-scoped rule"""
        payload = {
            "name": "Tagged Device Alert",
            "metric": "memory",
            "operator": ">",
            "threshold": 80.0,
            "window_n": 3,
            "required_k": 2,
            "cooldown_seconds": 60,
            "scope": "TAG",
            "tag": "critical",
            "enabled": True
        }
        
        response = client.post(
            f"/projects/{test_project.id}/rules",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["scope"] == "TAG"
        assert data["tag"] == "critical"
    
    def test_create_rule_invalid_operator(
        self,
        client,
        test_api_key,
        test_project
    ):
        """Test that invalid operators are rejected"""
        payload = {
            "name": "Bad Rule",
            "metric": "temp",
            "operator": "==",  # Invalid
            "threshold": 80.0,
            "window_n": 1,
            "required_k": 1,
            "cooldown_seconds": 60,
            "scope": "ALL"
        }
        
        response = client.post(
            f"/projects/{test_project.id}/rules",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 422
    
    def test_create_rule_k_greater_than_n_rejected(
        self,
        client,
        test_api_key,
        test_project
    ):
        """Test that required_k > window_n is rejected"""
        payload = {
            "name": "Invalid K/N",
            "metric": "temp",
            "operator": ">",
            "threshold": 80.0,
            "window_n": 3,
            "required_k": 5,  # Greater than window_n
            "cooldown_seconds": 60,
            "scope": "ALL"
        }
        
        response = client.post(
            f"/projects/{test_project.id}/rules",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 400
    
    def test_tag_scope_requires_tag(
        self,
        client,
        test_api_key,
        test_project
    ):
        """Test that TAG scope requires a tag value"""
        payload = {
            "name": "Missing Tag",
            "metric": "temp",
            "operator": ">",
            "threshold": 80.0,
            "window_n": 1,
            "required_k": 1,
            "cooldown_seconds": 60,
            "scope": "TAG",
            "tag": None  # Missing
        }
        
        response = client.post(
            f"/projects/{test_project.id}/rules",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 422
    
    def test_list_rules(
        self,
        client,
        test_api_key,
        test_project,
        test_rule
    ):
        """Test listing rules for a project"""
        response = client.get(
            f"/projects/{test_project.id}/rules",
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(r["id"] == test_rule.id for r in data)
    
    def test_update_rule(
        self,
        client,
        test_api_key,
        test_rule
    ):
        """Test updating a rule"""
        payload = {
            "threshold": 85.0,
            "cooldown_seconds": 600
        }
        
        response = client.patch(
            f"/rules/{test_rule.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == 85.0
        assert data["cooldown_seconds"] == 600
    
    def test_disable_rule(
        self,
        client,
        test_api_key,
        test_rule
    ):
        """Test disabling a rule"""
        payload = {"enabled": False}
        
        response = client.patch(
            f"/rules/{test_rule.id}",
            json=payload,
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
    
    def test_delete_rule(
        self,
        client,
        test_api_key,
        test_rule
    ):
        """Test deleting a rule"""
        response = client.delete(
            f"/rules/{test_rule.id}",
            headers={"X-API-Key": test_api_key.raw_key}
        )
        
        assert response.status_code == 204