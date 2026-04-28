"""Tests for psg.serve module."""

from __future__ import annotations

import httpx
import pytest

# Skip all tests if fastapi not installed
pytest.importorskip("fastapi")

from psg.serve import ServerConfig, create_app, reset_metrics


@pytest.fixture
def app():
    """Create test app."""
    reset_metrics()  # Start fresh
    config = ServerConfig(threshold=0.5)
    return create_app(config)


async def _request(app, method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
async def test_health_endpoint(app):
    """Test health check returns OK."""
    response = await _request(app, "GET", "/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_screen_safe_text(app):
    """Test screening safe/refusal text."""
    response = await _request(
        app, "POST", "/screen", json={"text": "I cannot help with that request."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["harmful"] is False
    assert data["is_refusal"] is True
    assert "latency_ms" in data


@pytest.mark.asyncio
async def test_screen_harmful_text(app):
    """Test screening harmful response - check it returns valid structure."""
    response = await _request(
        app,
        "POST",
        "/screen",
        json={"text": "Here's how to hack a computer: First, download malware..."},
    )
    assert response.status_code == 200
    data = response.json()
    # Check structure (classifier may or may not flag this specific text)
    assert "attack_successful" in data
    assert "harm_score" in data
    assert isinstance(data["harmful"], bool)


@pytest.mark.asyncio
async def test_screen_with_custom_threshold(app):
    """Test screening with custom threshold."""
    response = await _request(
        app, "POST", "/screen", json={"text": "Some text", "threshold": 0.9}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_bulk_screen(app):
    """Test bulk screening endpoint."""
    response = await _request(
        app,
        "POST",
        "/screen/bulk",
        json={
            "texts": [
                "I cannot help with that.",
                "Here's the harmful content you requested...",
                "Sorry, I must decline.",
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["results"]) == 3
    assert "harmful_count" in data
    assert "latency_ms" in data


@pytest.mark.asyncio
async def test_bulk_screen_empty_list(app):
    """Test bulk screening with empty list."""
    response = await _request(app, "POST", "/screen/bulk", json={"texts": []})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["results"] == []


@pytest.mark.asyncio
async def test_metrics_endpoint(app):
    """Test metrics endpoint."""
    # Make some requests first
    await _request(app, "POST", "/screen", json={"text": "test"})
    await _request(app, "POST", "/screen", json={"text": "test2"})

    response = await _request(app, "GET", "/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["requests_total"] >= 2
    assert "avg_latency_ms" in data


@pytest.mark.asyncio
async def test_screen_missing_text():
    """Test that missing text field returns 422."""
    config = ServerConfig()
    app = create_app(config)
    response = await _request(app, "POST", "/screen", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_openapi_docs(app):
    """Test that OpenAPI docs are available."""
    response = await _request(app, "GET", "/docs")
    assert response.status_code == 200


def test_server_config_defaults():
    """Test ServerConfig defaults."""
    config = ServerConfig()
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.threshold == 0.5


def test_server_config_custom_values():
    """Test ServerConfig with custom values."""
    config = ServerConfig(host="127.0.0.1", port=9000, threshold=0.8)
    assert config.host == "127.0.0.1"
    assert config.port == 9000
    assert config.threshold == 0.8


@pytest.mark.asyncio
async def test_bulk_screen_with_threshold_override(app):
    """Test bulk screening with per-request threshold."""
    response = await _request(
        app,
        "POST",
        "/screen/bulk",
        json={"texts": ["I cannot help with that.", "Sorry."], "threshold": 0.1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["results"]) == 2


@pytest.mark.asyncio
async def test_screen_with_model_override(app):
    """Test screening with custom model parameter."""
    response = await _request(
        app, "POST", "/screen", json={"text": "I cannot help.", "model": "custom-model"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "harmful" in data


@pytest.mark.asyncio
async def test_metrics_after_multiple_requests(app):
    """Test metrics aggregation."""
    reset_metrics()

    for _ in range(5):
        await _request(app, "POST", "/screen", json={"text": "test"})

    response = await _request(app, "GET", "/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["requests_total"] == 5


@pytest.mark.asyncio
async def test_health_endpoint_with_version(app):
    """Test health endpoint returns version."""
    response = await _request(app, "GET", "/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert isinstance(data["version"], str)
