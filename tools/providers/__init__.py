"""LLM Providers"""
from .base import BaseProvider, Response
from .ollama import OllamaProvider
from .groq import GroqProvider


def get_provider(provider_name: str, model: str, **kwargs) -> BaseProvider:
    """Factory function to get provider by name"""
    providers = {
        "ollama": OllamaProvider,
        "groq": GroqProvider,
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Options: {list(providers.keys())}")
    
    return providers[provider_name](model, **kwargs)


__all__ = ["BaseProvider", "Response", "OllamaProvider", "GroqProvider", "get_provider"]
