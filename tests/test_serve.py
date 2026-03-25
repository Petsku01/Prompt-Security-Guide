"""Tests for psg.serve module."""
from __future__ import annotations

import pytest

# Skip all tests if fastapi not installed
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from psg.serve import ServerConfig, create_app, reset_metrics


@pytest.fixture
def client():
    """Create test client."""
    reset_metrics()  # Start fresh
    config = ServerConfig(threshold=0.5)
    app = create_app(config)
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check returns OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_screen_safe_text(client):
    """Test screening safe/refusal text."""
    response = client.post("/screen", json={"text": "I cannot help with that request."})
    assert response.status_code == 200
    data = response.json()
    assert data["harmful"] is False
    assert data["is_refusal"] is True
    assert "latency_ms" in data


def test_screen_harmful_text(client):
    """Test screening harmful response - check it returns valid structure."""
    response = client.post("/screen", json={
        "text": "Here's how to hack a computer: First, download malware..."
    })
    assert response.status_code == 200
    data = response.json()
    # Check structure (classifier may or may not flag this specific text)
    assert "attack_successful" in data
    assert "harm_score" in data
    assert isinstance(data["harmful"], bool)


def test_screen_with_custom_threshold(client):
    """Test screening with custom threshold."""
    response = client.post("/screen", json={
        "text": "Some text",
        "threshold": 0.9
    })
    assert response.status_code == 200


def test_bulk_screen(client):
    """Test bulk screening endpoint."""
    response = client.post("/screen/bulk", json={
        "texts": [
            "I cannot help with that.",
            "Here's the harmful content you requested...",
            "Sorry, I must decline."
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["results"]) == 3
    assert "harmful_count" in data
    assert "latency_ms" in data


def test_bulk_screen_empty_list(client):
    """Test bulk screening with empty list."""
    response = client.post("/screen/bulk", json={"texts": []})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["results"] == []


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    # Make some requests first
    client.post("/screen", json={"text": "test"})
    client.post("/screen", json={"text": "test2"})
    
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["requests_total"] >= 2
    assert "avg_latency_ms" in data


def test_screen_missing_text():
    """Test that missing text field returns 422."""
    config = ServerConfig()
    app = create_app(config)
    client = TestClient(app)
    
    response = client.post("/screen", json={})
    assert response.status_code == 422


def test_openapi_docs(client):
    """Test that OpenAPI docs are available."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_server_config_defaults():
    """Test ServerConfig defaults."""
    config = ServerConfig()
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.threshold == 0.5
