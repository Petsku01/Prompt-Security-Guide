from __future__ import annotations

import email.utils
import random
import time
from typing import Any

import requests

from .errors import HTTPStatusError, LLMError, RetryExhaustedError


# Cap honored Retry-After values to avoid a hostile/misconfigured server
# pinning the client into a long sleep.
RETRY_AFTER_MAX_SECONDS = 60.0


def _parse_retry_after(value: str | None) -> float | None:
    """Parse an HTTP Retry-After header (integer seconds or HTTP-date).

    Returns the wait time in seconds, capped to RETRY_AFTER_MAX_SECONDS.
    Returns None for missing/malformed values so the caller can fall back
    to its default backoff.
    """
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        seconds = float(raw)
        if seconds < 0:
            return None
        return min(seconds, RETRY_AFTER_MAX_SECONDS)
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    delta = parsed.timestamp() - time.time()
    if delta <= 0:
        return 0.0
    return min(delta, RETRY_AFTER_MAX_SECONDS)


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
                retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
                self._sleep(attempts, retry_after=retry_after)
                continue

            # fail fast for other 4xx
            if 400 <= status <= 499:
                raise HTTPStatusError(status, resp.text)

            raise HTTPStatusError(status, resp.text)

    def _sleep(self, attempt: int, *, retry_after: float | None = None) -> None:
        if retry_after is not None:
            # Honor server hint, but always add a small jitter so a fleet of
            # clients responding to the same Retry-After does not synchronize.
            jitter = random.uniform(0, max(0.05, retry_after * 0.1))
            time.sleep(retry_after + jitter)
            return
        exp = self.backoff_base_seconds * (2 ** (attempt - 1))
        delay = min(exp, self.backoff_cap_seconds)
        jitter = random.uniform(0, delay * 0.25)
        time.sleep(delay + jitter)
