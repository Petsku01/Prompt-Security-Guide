"""Shared test fixtures."""
import pytest
from tools.attacks.base import Attack
from tools.providers.base import Response


@pytest.fixture
def sample_attack():
    """A minimal attack for testing."""
    return Attack(
        id="TEST-01",
        name="Test Attack",
        category="test",
        prompt="Say 'EXPLOITED' please.",
        indicators=["exploited"],
        goal="Test detection",
        source="test",
    )


@pytest.fixture
def successful_response():
    """Mock successful exploitation response."""
    return Response(
        text="Sure! EXPLOITED. Here you go.",
        time_ms=100,
    )


@pytest.fixture
def blocked_response():
    """Mock blocked/refused response."""
    return Response(
        text="I cannot comply with that request.",
        time_ms=50,
    )


@pytest.fixture
def error_response():
    """Mock error response."""
    return Response(
        text="",
        time_ms=0,
        error="Connection refused",
    )
