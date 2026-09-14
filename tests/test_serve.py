"""Tests for psg.serve module."""

from __future__ import annotations

import asyncio

import httpx
import pytest

# Skip all tests if fastapi not installed
pytest.importorskip("fastapi")

from psg.serve import ServerConfig, create_app, reset_metrics


@pytest.fixture
def app():
    """Create test app."""
    reset_metrics()  # Start fresh
    config = ServerConfig(host="127.0.0.1", rate_limit_per_minute=0)
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
    """Test ServerConfig defaults (audit P0: localhost, not 0.0.0.0)."""
    config = ServerConfig()
    assert config.host == "127.0.0.1"
    assert config.port == 8000
    assert config.threshold == 0.5
    assert config.api_key is None
    assert config.bulk_max_items == 1000
    assert config.rate_limit_per_minute == 120


def _run(app, method: str, path: str, **kwargs):
    """Run an ASGI request synchronously — independent of pytest-asyncio
    so the sync hardening tests work in every env."""

    async def _inner():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.new_event_loop().run_until_complete(_inner())


def test_server_config_public_bind_requires_api_key():
    """Audit P0: public bind without api_key must be rejected."""
    with pytest.raises(ValueError, match="api_key"):
        ServerConfig(host="0.0.0.0")
    # explicit public bind WITH a key is fine
    cfg = ServerConfig(host="0.0.0.0", api_key="secret")
    assert cfg.api_key == "secret"


def test_server_config_validates_threshold_and_limits():
    """ServerConfig validates threshold range and sane limits."""
    with pytest.raises(ValueError, match="threshold"):
        ServerConfig(threshold=1.5)
    with pytest.raises(ValueError, match="threshold"):
        ServerConfig(threshold=-0.1)
    with pytest.raises(ValueError, match="bulk_max_items"):
        ServerConfig(bulk_max_items=0)
    with pytest.raises(ValueError, match="rate_limit"):
        ServerConfig(rate_limit_per_minute=-1)


def test_bulk_screen_over_limit_returns_413(app):
    """Audit P0: bulk requests beyond bulk_max_items are rejected."""
    response = _run(
        app,
        "POST",
        "/screen/bulk",
        json={"texts": ["ok"] * (1000 + 1)},
    )
    assert response.status_code == 413


def test_bulk_screen_oversized_text_returns_413(app):
    """Audit P0: per-text char limit enforced."""
    response = _run(
        app,
        "POST",
        "/screen/bulk",
        json={"texts": ["x" * (100_000 + 1)]},
    )
    assert response.status_code == 413


def test_bulk_screen_normal_sizes_still_pass(app):
    """Sanity: legit bulk traffic under the limits still screens fine."""
    response = _run(
        app,
        "POST",
        "/screen/bulk",
        json={"texts": ["I cannot help with that.", "Sorry."]},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_screen_rejects_out_of_range_threshold(app):
    """Pydantic ge/le must reject thresholds outside [0, 1]."""
    response = _run(app, "POST", "/screen", json={"text": "hello", "threshold": 2.5})
    assert response.status_code == 422


def test_auth_required_when_api_key_set():
    """Audit P0: with api_key set, requests without/with-wrong key get 401."""
    reset_metrics()
    app = create_app(
        ServerConfig(
            host="127.0.0.1",
            rate_limit_per_minute=0,
            api_key="test-secret-123",
        )
    )
    response = _run(app, "POST", "/screen", json={"text": "hello"})
    assert response.status_code == 401
    response = _run(
        app,
        "POST",
        "/screen",
        json={"text": "hello"},
        headers={"X-API-Key": "wrong"},
    )
    assert response.status_code == 401
    response = _run(
        app,
        "POST",
        "/screen",
        json={"text": "hello"},
        headers={"X-API-Key": "test-secret-123"},
    )
    assert response.status_code == 200
    response = _run(app, "GET", "/health")
    assert response.status_code == 200  # health stays open


def test_rate_limit_returns_429():
    """Audit P0: per-client rate limit returns 429 when exhausted."""
    reset_metrics()
    app = create_app(
        ServerConfig(host="127.0.0.1", rate_limit_per_minute=3, threshold=0.5)
    )
    for _ in range(3):
        response = _run(app, "POST", "/screen", json={"text": "test"})
        assert response.status_code == 200
    response = _run(app, "POST", "/screen", json={"text": "test"})
    assert response.status_code == 429


def test_enforce_server_threshold_rejects_override():
    """Audit P0: enforce_server_threshold forbids client threshold."""
    reset_metrics()
    app = create_app(
        ServerConfig(
            host="127.0.0.1",
            rate_limit_per_minute=0,
            enforce_server_threshold=True,
            threshold=0.9,
        )
    )
    response = _run(app, "POST", "/screen", json={"text": "hello", "threshold": 0.1})
    assert response.status_code == 400
    # without override — server threshold applies, normal path
    response = _run(app, "POST", "/screen", json={"text": "hello"})
    assert response.status_code == 200


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
