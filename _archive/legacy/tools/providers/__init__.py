"""LLM Providers"""
from .base import BaseProvider, Response
from .ollama import OllamaProvider


def get_provider(provider_name: str, model: str, **kwargs) -> BaseProvider:
    """Factory function to get provider by name"""
    providers = {
        "ollama": OllamaProvider,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Options: {list(providers.keys())}")

    return providers[provider_name](model, **kwargs)


__all__ = ["BaseProvider", "Response", "OllamaProvider", "get_provider"]
