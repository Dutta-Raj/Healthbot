"""
Unit tests for API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

class TestAPIEndpoints:
    """Test FastAPI endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from main_api import app
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "message" in response.json()
    
    @patch('main_api.process_query')
    def test_chat_endpoint_success(self, mock_process, client):
        """Test successful chat endpoint"""
        mock_process.return_value = {
            "response": "Your blood pressure is normal",
            "confidence": 0.95,
            "intent": "blood_pressure_query"
        }
        
        response = client.post("/chat", json={
            "message": "What is my blood pressure?",
            "user_id": "test_user",
            "session_id": "session_123"
        })
        
        assert response.status_code == 200
        assert "response" in response.json()
        assert response.json()["confidence"] > 0.9
    
    def test_chat_endpoint_empty_message(self, client):
        """Test chat with empty message"""
        response = client.post("/chat", json={
            "message": "",
            "user_id": "test_user"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_endpoint_missing_user(self, client):
        """Test chat without user_id"""
        response = client.post("/chat", json={
            "message": "Hello"
        })
        
        assert response.status_code == 422
    
    @patch('main_api.get_conversation_history')
    def test_get_history_endpoint(self, mock_history, client):
        """Test conversation history endpoint"""
        mock_history.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        response = client.get("/history/test_user")
        
        assert response.status_code == 200
        assert len(response.json()) == 2
    
    @patch('main_api.clear_conversation')
    def test_clear_history_endpoint(self, mock_clear, client):
        """Test clearing conversation history"""
        mock_clear.return_value = {"status": "success"}
        
        response = client.delete("/history/test_user")
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    @patch('main_api.rate_limit_check')
    def test_rate_limiting(self, mock_rate_limit, client):
        """Test rate limiting"""
        mock_rate_limit.return_value = False  # Rate limit exceeded
        
        response = client.post("/chat", json={
            "message": "Test message",
            "user_id": "test_user"
        })
        
        assert response.status_code == 429  # Too Many Requests
    
    def test_invalid_json_payload(self, client):
        """Test invalid JSON payload"""
        response = client.post("/chat", data="invalid json")
        
        assert response.status_code == 400
    
    @patch('main_api.authenticate_user')
    def test_protected_endpoint(self, mock_auth, client):
        """Test protected endpoint authentication"""
        mock_auth.return_value = {"user_id": "test_user", "authenticated": True}
        
        response = client.get("/protected", headers={
            "Authorization": "Bearer valid_token"
        })
        
        assert response.status_code == 200
    
    @patch('main_api.authenticate_user')
    def test_protected_endpoint_no_auth(self, mock_auth, client):
        """Test protected endpoint without authentication"""
        mock_auth.return_value = None
        
        response = client.get("/protected")
        
        assert response.status_code == 401
