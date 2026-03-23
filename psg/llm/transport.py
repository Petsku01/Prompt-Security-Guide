from __future__ import annotations

import random
import time
from typing import Any

import requests

from .errors import HTTPStatusError, LLMError, RetryExhaustedError


class Transport:
    def __init__(
        self,
        timeout_seconds: float = 60.0,
        max_retries: int = 4,
        backoff_base_seconds: float = 0.6,
        backoff_cap_seconds: float = 8.0,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_cap_seconds = backoff_cap_seconds

    def post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        attempts = 0
        request_headers = dict(headers or {})
        while True:
            attempts += 1
            try:
                resp = requests.post(url, json=payload, headers=request_headers, timeout=self.timeout_seconds)
            except requests.RequestException as exc:
                if attempts > self.max_retries:
                    raise RetryExhaustedError(f"request failed after retries: {exc}") from exc
                self._sleep(attempts)
                continue

            status = resp.status_code
            if 200 <= status < 300:
                try:
                    return resp.json()
                except ValueError as exc:
                    raise LLMError(f"invalid JSON response: {resp.text[:300]}") from exc

            # retry 429 and server errors
            if status == 429 or 500 <= status <= 599:
                if attempts > self.max_retries:
                    raise RetryExhaustedError(f"retries exhausted with status {status}: {resp.text[:300]}")
                self._sleep(attempts)
                continue

            # fail fast for other 4xx
            if 400 <= status <= 499:
                raise HTTPStatusError(status, resp.text)

            raise HTTPStatusError(status, resp.text)

    def _sleep(self, attempt: int) -> None:
        exp = self.backoff_base_seconds * (2 ** (attempt - 1))
        delay = min(exp, self.backoff_cap_seconds)
        jitter = random.uniform(0, delay * 0.25)
        time.sleep(delay + jitter)
