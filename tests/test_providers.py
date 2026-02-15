"""Tests for provider factory and response metadata."""
import pytest
from tools.providers import get_provider
from tools.providers.ollama import OllamaProvider


def test_get_provider_ollama_type():
    provider = get_provider("ollama", "qwen2.5:3b")
    assert isinstance(provider, OllamaProvider)


def test_get_provider_unknown_raises():
    with pytest.raises(ValueError):
        get_provider("nope", "model")


def test_ollama_stores_seed_and_temperature():
    provider = OllamaProvider("qwen2.5:3b", seed=42, temperature=0.5)
    assert provider.seed == 42
    assert provider.temperature == 0.5
