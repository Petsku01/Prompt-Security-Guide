"""FastAPI server for real-time prompt/response screening.

Usage:
    psg serve --port 8000
    psg serve --port 8000 --threshold 0.6

Endpoints:
    POST /screen      - Screen text for harmful content
    POST /screen/bulk - Screen multiple texts
    GET  /health      - Health check
    GET  /metrics     - Prometheus metrics (if enabled)
"""

from __future__ import annotations

import argparse
import hmac
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

    # Dummy classes for when FastAPI not installed
    class BaseModel:  # type: ignore[no-redef]
        pass

    def Field(*args, **kwargs):  # type: ignore[no-redef]
        return None


from .security.classifier import classify_response_v2  # noqa: E402


@dataclass
class ServerConfig:
    """Server configuration.

    host defaults to 127.0.0.1 (audit P0: a screening API must not be
    exposed to the network without an explicit decision). Bind a public
    interface only together with api_key.
    """

    host: str = "127.0.0.1"
    port: int = 8000
    threshold: float = 0.5
    enable_metrics: bool = False
    api_key: str | None = None  # when set, requests must send X-API-Key
    bulk_max_items: int = 1000
    bulk_max_text_chars: int = 100_000
    rate_limit_per_minute: int = 120  # 0 disables
    enforce_server_threshold: bool = False  # reject client threshold overrides

    def __post_init__(self) -> None:
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError(f"threshold must be in [0, 1], got {self.threshold}")
        if self.bulk_max_items < 1:
            raise ValueError(f"bulk_max_items must be >= 1, got {self.bulk_max_items}")
        if self.bulk_max_text_chars < 1:
            raise ValueError(
                f"bulk_max_text_chars must be >= 1, got {self.bulk_max_text_chars}"
            )
        if self.rate_limit_per_minute < 0:
            raise ValueError(
                f"rate_limit_per_minute must be >= 0, got {self.rate_limit_per_minute}"
            )
        exposed = self.host not in ("127.0.0.1", "localhost", "::1")
        if exposed and not self.api_key:
            raise ValueError(
                f"binding to {self.host!r} requires api_key — a screening API "
                "must not be exposed unauthenticated; set api_key or bind to "
                "127.0.0.1"
            )


# Pydantic models (must be at module level for FastAPI)
class ScreenRequest(BaseModel):
    text: str = Field(..., description="Text to screen for harmful content")
    threshold: float | None = Field(
        None, description="Override default threshold", ge=0.0, le=1.0
    )


class ScreenResponse(BaseModel):
    harmful: bool
    harm_score: float
    is_refusal: bool
    has_disclaimer: bool
    attack_successful: bool
    latency_ms: float


class BulkScreenRequest(BaseModel):
    texts: list[str] = Field(..., description="List of texts to screen")
    threshold: float | None = Field(
        None, description="Override default threshold", ge=0.0, le=1.0
    )


class BulkScreenResponse(BaseModel):
    results: list[ScreenResponse]
    total: int
    harmful_count: int
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    version: str


class MetricsResponse(BaseModel):
    requests_total: int
    requests_harmful: int
    requests_safe: int
    avg_latency_ms: float


# Metrics (simple in-memory counters)
_metrics: dict[str, Any] = {
    "requests_total": 0,
    "requests_harmful": 0,
    "requests_safe": 0,
    "latency_sum_ms": 0.0,
}


def reset_metrics() -> None:
    _metrics["requests_total"] = 0
    _metrics["requests_harmful"] = 0
    _metrics["requests_safe"] = 0
    _metrics["latency_sum_ms"] = 0.0


# --- per-client rate limiting (fixed window, in-memory, per-process) ---
_rate_state: dict[str, tuple[int, float]] = {}  # client_key -> (count, window_start)
_RATE_LOCK = threading.Lock()


def _rate_limit_check(client_key: str, limit_per_minute: int) -> bool:
    """Return True when the client is within the per-minute limit."""
    if limit_per_minute <= 0:
        return True
    now = time.time()
    with _RATE_LOCK:
        count, window_start = _rate_state.get(client_key, (0, now))
        if now - window_start >= 60.0:
            count, window_start = 0, now
        if count >= limit_per_minute:
            return False
        _rate_state[client_key] = (count + 1, window_start)
        return True


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def create_app(config: ServerConfig | None = None) -> "FastAPI":
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI not installed. Install with: pip install fastapi uvicorn"
        )

    cfg = config or ServerConfig()
    from . import __version__

    app = FastAPI(
        title="PSG Screening API",
        description="Real-time prompt and response screening for LLM safety",
        version=__version__,
    )

    async def _guard(request: Request) -> JSONResponse | None:
        """Shared auth + rate-limit guard for screening endpoints."""
        if cfg.api_key:
            supplied = request.headers.get("X-API-Key")
            if not supplied or not hmac.compare_digest(supplied, cfg.api_key):
                return JSONResponse(
                    status_code=401, content={"detail": "invalid or missing API key"}
                )
        if not _rate_limit_check(_client_ip(request), cfg.rate_limit_per_minute):
            return JSONResponse(
                status_code=429, content={"detail": "rate limit exceeded"}
            )
        return None

    async def _effective_threshold(body_threshold: float | None) -> float:
        if cfg.enforce_server_threshold and body_threshold is not None:
            raise HTTPException(
                status_code=400,
                detail="server threshold policy forbids client threshold override",
            )
        return body_threshold if body_threshold is not None else cfg.threshold

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Health check endpoint."""
        from . import __version__

        return HealthResponse(status="ok", version=__version__)

    @app.post("/screen", response_model=ScreenResponse)
    async def screen(body: ScreenRequest, request: Request) -> ScreenResponse:
        """Screen a single text for harmful content."""
        denied = await _guard(request)
        if denied is not None:
            return denied  # type: ignore[return-value]
        start = time.perf_counter()

        result = classify_response_v2(body.text)
        threshold = await _effective_threshold(body.threshold)
        harmful = result.harm_score >= threshold and result.attack_successful

        latency_ms = (time.perf_counter() - start) * 1000

        # Update metrics
        _metrics["requests_total"] += 1
        _metrics["latency_sum_ms"] += latency_ms
        if harmful:
            _metrics["requests_harmful"] += 1
        else:
            _metrics["requests_safe"] += 1

        return ScreenResponse(
            harmful=harmful,
            harm_score=result.harm_score,
            is_refusal=result.is_refusal,
            has_disclaimer=result.has_disclaimer,
            attack_successful=result.attack_successful,
            latency_ms=round(latency_ms, 2),
        )

    @app.post("/screen/bulk", response_model=BulkScreenResponse)
    async def screen_bulk(
        body: BulkScreenRequest, request: Request
    ) -> BulkScreenResponse | JSONResponse:
        """Screen multiple texts for harmful content."""
        denied = await _guard(request)
        if denied is not None:
            return denied
        if len(body.texts) > cfg.bulk_max_items:
            raise HTTPException(
                status_code=413,
                detail=f"bulk request exceeds bulk_max_items={cfg.bulk_max_items}",
            )
        oversized = [
            i for i, t in enumerate(body.texts) if len(t) > cfg.bulk_max_text_chars
        ]
        if oversized:
            raise HTTPException(
                status_code=413,
                detail=(
                    "text length exceeds bulk_max_text_chars="
                    f"{cfg.bulk_max_text_chars} at indexes {oversized[:5]}"
                ),
            )

        start = time.perf_counter()

        threshold = await _effective_threshold(body.threshold)
        results: list[ScreenResponse] = []
        harmful_count = 0

        for text in body.texts:
            text_start = time.perf_counter()
            result = classify_response_v2(text)
            harmful = result.harm_score >= threshold and result.attack_successful
            text_latency = (time.perf_counter() - text_start) * 1000

            if harmful:
                harmful_count += 1

            results.append(
                ScreenResponse(
                    harmful=harmful,
                    harm_score=result.harm_score,
                    is_refusal=result.is_refusal,
                    has_disclaimer=result.has_disclaimer,
                    attack_successful=result.attack_successful,
                    latency_ms=round(text_latency, 2),
                )
            )

        total_latency = (time.perf_counter() - start) * 1000

        # Update metrics
        _metrics["requests_total"] += len(body.texts)
        _metrics["latency_sum_ms"] += total_latency
        _metrics["requests_harmful"] += harmful_count
        _metrics["requests_safe"] += len(body.texts) - harmful_count

        return BulkScreenResponse(
            results=results,
            total=len(results),
            harmful_count=harmful_count,
            latency_ms=round(total_latency, 2),
        )

    @app.get("/metrics", response_model=MetricsResponse)
    async def metrics() -> MetricsResponse:
        """Get server metrics."""
        avg_latency = (
            _metrics["latency_sum_ms"] / _metrics["requests_total"]
            if _metrics["requests_total"] > 0
            else 0.0
        )
        return MetricsResponse(
            requests_total=_metrics["requests_total"],
            requests_harmful=_metrics["requests_harmful"],
            requests_safe=_metrics["requests_safe"],
            avg_latency_ms=round(avg_latency, 2),
        )

    return app


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for serve command."""
    parser = argparse.ArgumentParser(
        description="Start PSG screening API server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1 — public bind requires --api-key)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Default confidence threshold (default: 0.5)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Require X-API-Key header on screening endpoints. "
        "Also via PSG_API_KEY env. Required when binding a public host.",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=120,
        help="Screening requests per client per minute (0 disables; default: 120)",
    )
    parser.add_argument(
        "--bulk-max-items",
        type=int,
        default=1000,
        help="Max texts per bulk request (default: 1000)",
    )
    parser.add_argument(
        "--enforce-server-threshold",
        action="store_true",
        help="Reject client threshold overrides (server threshold is authoritative)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the server."""
    if not FASTAPI_AVAILABLE:
        logger.error("FastAPI not installed. Install with: pip install fastapi uvicorn")
        return 1

    try:
        import uvicorn
    except ImportError:
        logger.error("uvicorn not installed. Install with: pip install uvicorn")
        return 1

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = ServerConfig(
            host=args.host,
            port=args.port,
            threshold=args.threshold,
            api_key=args.api_key or os.environ.get("PSG_API_KEY") or None,
            rate_limit_per_minute=args.rate_limit,
            bulk_max_items=args.bulk_max_items,
            enforce_server_threshold=args.enforce_server_threshold,
        )
    except ValueError as exc:
        logger.error("Invalid server configuration: %s", exc)
        return 2

    logger.info("Starting PSG server on %s:%d", config.host, config.port)
    logger.info("Default threshold: %s", config.threshold)
    logger.info("Docs: http://%s:%d/docs", config.host, config.port)

    # Create app with config
    app = create_app(config)

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        reload=args.reload,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
