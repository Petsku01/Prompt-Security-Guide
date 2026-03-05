"""Ollama provider for local models"""
import time
import requests
from typing import Optional
from .base import BaseProvider, Response


class OllamaProvider(BaseProvider):
    """Provider for local Ollama models"""

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        seed: Optional[int] = None,
        temperature: float = 0.7,
    ):
        self.model = model
        self.base_url = base_url
        self.timeout = 120
        self.seed = seed
        self.temperature = temperature

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    def call(self, prompt: str, system_prompt: Optional[str] = None) -> Response:
        url = f"{self.base_url}/api/generate"
        options = {"temperature": self.temperature}
        if self.seed is not None:
            options["seed"] = self.seed

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if system_prompt:
            payload["system"] = system_prompt

        retry_delays = [1, 2, 4]
        start = time.time()

        for attempt in range(len(retry_delays) + 1):
            try:
                resp = requests.post(url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                elapsed = int((time.time() - start) * 1000)
                return Response(
                    text=resp.json().get("response", ""),
                    time_ms=elapsed,
                    seed_used=self.seed,
                    temperature_used=self.temperature,
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt >= len(retry_delays):
                    elapsed = int((time.time() - start) * 1000)
                    return Response(
                        text="",
                        time_ms=elapsed,
                        error=str(e),
                        seed_used=self.seed,
                        temperature_used=self.temperature,
                    )
                time.sleep(retry_delays[attempt])
            except Exception as e:
                elapsed = int((time.time() - start) * 1000)
                return Response(
                    text="",
                    time_ms=elapsed,
                    error=str(e),
                    seed_used=self.seed,
                    temperature_used=self.temperature,
                )
