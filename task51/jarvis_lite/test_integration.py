"""
Integration tests for Jarvis-Lite API and 3D UI
Tests the full end-to-end flow: chat -> agent -> response
"""

import pytest
import json
from fastapi.testclient import TestClient
from api import app

# Create test client
client = TestClient(app)

class TestAPIHealth:
    """Health check and basic endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns status"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "docs" in data
    
    def test_health_endpoint(self):
        """Test health check"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert data["services"]["agent"] == "ready"

class TestChatEndpoint:
    """Chat functionality tests"""
    
    def test_basic_chat_message(self):
        """Test sending a simple message"""
        response = client.post("/chat", json={
            "message": "Hello, what can you do?",
            "memory_type": "buffer",
            "language": "en"
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "tool_used" in data
        assert "confidence" in data
        assert isinstance(data["confidence"], (int, float))
        assert 0 <= data["confidence"] <= 1
    
    def test_calculator_intent(self):
        """Test calculator tool detection"""
        response = client.post("/chat", json={
            "message": "Calculate 2 + 2",
            "memory_type": "buffer"
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        # Should recognize as calculator (not required to be exact)
        assert len(data["answer"]) > 0
    
    def test_weather_intent(self):
        """Test weather tool detection"""
        response = client.post("/chat", json={
            "message": "What's the weather in London?",
            "memory_type": "buffer"
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
    
    def test_chat_with_sources(self):
        """Test chat response with document sources"""
        response = client.post("/chat", json={
            "message": "Search my documents for refund policy",
            "memory_type": "buffer"
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        # May or may not have sources (depends on documents)
        if "sources" in data:
            assert isinstance(data["sources"], list)

class TestMemoryEndpoints:
    """Conversation memory tests"""
    
    def test_get_empty_history(self):
        """Test retrieving empty conversation history"""
        response = client.get("/memory/history?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)
    
    def test_clear_memory(self):
        """Test clearing memory"""
        response = client.post("/memory/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
    
    def test_get_stats(self):
        """Test getting session stats"""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "memory_messages" in data

class TestSettingsModal:
    """Settings persistence tests"""
    
    def test_settings_schema(self):
        """Test that settings can be applied through chat"""
        response = client.post("/chat", json={
            "message": "Test message",
            "memory_type": "summary",  # Test summary memory
            "language": "hi"  # Test Hindi
        })
        assert response.status_code == 200

class TestErrorHandling:
    """Error handling and edge cases"""
    
    def test_empty_message(self):
        """Test handling of empty message"""
        # API should either handle gracefully or return error
        response = client.post("/chat", json={
            "message": "",
            "memory_type": "buffer"
        })
        # Should not crash (5xx error)
        assert response.status_code < 500
    
    def test_very_long_message(self):
        """Test handling of very long input"""
        long_message = "hello " * 1000  # 6000+ characters
        response = client.post("/chat", json={
            "message": long_message,
            "memory_type": "buffer"
        })
        # Should handle without crashing
        assert response.status_code < 500
    
    def test_missing_required_field(self):
        """Test missing required fields"""
        response = client.post("/chat", json={
            "memory_type": "buffer"
            # Missing 'message' field
        })
        assert response.status_code == 422  # Validation error

class TestWebSocketChat:
    """WebSocket functionality tests (if running server)"""
    
    def test_websocket_connection(self):
        """Test WebSocket connection"""
        with client.websocket_connect("/ws/chat") as websocket:
            # Send a message
            websocket.send_json({"message": "Hello via WebSocket"})
            
            # Receive response
            data = websocket.receive_json()
            assert "type" in data
            assert data["type"] in ["response", "error"]

class TestUIIntegration:
    """3D UI integration tests"""
    
    def test_static_files_served(self):
        """Test that static files (HTML/CSS/JS) are served"""
        # HTML
        response = client.get("/static/index.html")
        assert response.status_code == 200
        assert "Jarvis-Lite" in response.text
        assert "canvas3d" in response.text
        
        # CSS
        response = client.get("/static/style.css")
        assert response.status_code == 200
        assert "--primary: #00d9ff" in response.text or "00d9ff" in response.text
        
        # JavaScript
        response = client.get("/static/script.js")
        assert response.status_code == 200
        assert "Three.js" in response.text or "THREE" in response.text or "initThreeJS" in response.text

class TestResponseFormat:
    """Verify response formats match frontend expectations"""
    
    def test_chat_response_format(self):
        """Verify chat response includes all required fields for UI"""
        response = client.post("/chat", json={
            "message": "Test",
            "memory_type": "buffer"
        })
        data = response.json()
        
        # Check all fields expected by script.js
        assert "answer" in data
        assert "tool_used" in data
        assert "confidence" in data
        assert "sources" in data  # May be empty list
        assert isinstance(data["sources"], list)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
