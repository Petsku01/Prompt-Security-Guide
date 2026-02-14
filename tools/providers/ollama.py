"""Ollama provider for local models"""
import time
import requests
from typing import Optional
from .base import BaseProvider, Response


class OllamaProvider(BaseProvider):
    """Provider for local Ollama models"""
    
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.timeout = 120
    
    @property
    def name(self) -> str:
        return f"ollama/{self.model}"
    
    def call(self, prompt: str, system_prompt: Optional[str] = None) -> Response:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7}
        }
        if system_prompt:
            payload["system"] = system_prompt
        
        start = time.time()
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            elapsed = int((time.time() - start) * 1000)
            return Response(
                text=resp.json().get("response", ""),
                time_ms=elapsed
            )
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return Response(text="", time_ms=elapsed, error=str(e))
