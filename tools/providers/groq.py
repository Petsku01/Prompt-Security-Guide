"""Groq provider for cloud models"""
import os
import time
import requests
from typing import Optional
from .base import BaseProvider, Response


class GroqProvider(BaseProvider):
    """Provider for Groq API models"""
    
    def __init__(self, model: str, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.timeout = 60
        
        if not self.api_key:
            raise ValueError("Groq API key required (pass api_key or set GROQ_API_KEY)")
    
    @property
    def name(self) -> str:
        return f"groq/{self.model}"
    
    def call(self, prompt: str, system_prompt: Optional[str] = None) -> Response:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        start = time.time()
        try:
            resp = requests.post(
                self.base_url, 
                headers=headers, 
                json=payload, 
                timeout=self.timeout
            )
            resp.raise_for_status()
            elapsed = int((time.time() - start) * 1000)
            return Response(
                text=resp.json()["choices"][0]["message"]["content"],
                time_ms=elapsed
            )
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return Response(text="", time_ms=elapsed, error=str(e))
