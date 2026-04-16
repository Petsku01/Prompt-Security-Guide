"""FastAPI server for real-time prompt/response screening.

Usage:
    psg serve --port 8000                              # binds 127.0.0.1
    psg serve --port 8000 --allow-public               # binds 0.0.0.0
    psg serve --port 8000 --api-key SECRET             # require X-API-Key header
    PSG_SERVE_API_KEY=SECRET psg serve --port 8000     # same, via env

Endpoints:
    POST /screen      - Screen text for harmful content
    POST /screen/bulk - Screen multiple texts
    GET  /health      - Health check (calls classifier on a probe input)
    GET  /metrics     - In-memory metrics

Security defaults:
    - Binds to 127.0.0.1 unless --allow-public is set.
    - When PSG_SERVE_API_KEY (or --api-key) is set, all routes except
      /health require an X-API-Key header that matches.
    - Request bodies larger than MAX_REQUEST_BYTES are rejected with 413.
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
    from pydantic import BaseModel, Field
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Dummy classes so the module still imports without FastAPI installed.
    class BaseModel:  # type: ignore
        pass
    def Field(*args, **kwargs):  # type: ignore
        return None
    def Depends(*_args, **_kwargs):  # type: ignore
        return None
    def Header(*_args, **_kwargs):  # type: ignore
        return None
    class HTTPException(Exception):  # type: ignore
        def __init__(self, status_code: int, detail: str = "") -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail
    class status:  # type: ignore
        HTTP_401_UNAUTHORIZED = 401
        HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413
        HTTP_503_SERVICE_UNAVAILABLE = 503

from .security.classifier import classify_response_v2


MAX_REQUEST_BYTES = 64 * 1024  # 64 KiB
HEALTH_PROBE_TEXT = "ok"


@dataclass
class ServerConfig:
    """Server configuration.

    Note: ``host`` defaults to 127.0.0.1. Use ``--allow-public`` (which sets
    host to 0.0.0.0) only on a trusted network or behind a reverse proxy.
    """
    host: str = "127.0.0.1"
    port: int = 8000
    threshold: float = 0.5
    enable_metrics: bool = False
    api_key: str | None = None
    max_request_bytes: int = MAX_REQUEST_BYTES


# Pydantic models (must be at module level for FastAPI)
class ScreenRequest(BaseModel):
    text: str = Field(..., description="Text to screen for harmful content")
    threshold: float | None = Field(None, description="Override default threshold")


class ScreenResponse(BaseModel):
    harmful: bool
    harm_score: float
    is_refusal: bool
    has_disclaimer: bool
    attack_successful: bool
    latency_ms: float


class BulkScreenRequest(BaseModel):
    texts: list[str] = Field(..., description="List of texts to screen")
    threshold: float | None = Field(None, description="Override default threshold")


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


# Thread-safe metrics. uvicorn may dispatch handlers across threads; the prior
# unguarded dict allowed lost updates under concurrent load.
_metrics_lock = threading.Lock()
_metrics: dict[str, Any] = {
    "requests_total": 0,
    "requests_harmful": 0,
    "requests_safe": 0,
    "latency_sum_ms": 0.0,
}


def _record_metric(*, harmful: bool, latency_ms: float) -> None:
    with _metrics_lock:
        _metrics["requests_total"] += 1
        _metrics["latency_sum_ms"] += latency_ms
        if harmful:
            _metrics["requests_harmful"] += 1
        else:
            _metrics["requests_safe"] += 1


def _record_metrics_bulk(*, total: int, harmful_count: int, latency_ms: float) -> None:
    with _metrics_lock:
        _metrics["requests_total"] += total
        _metrics["latency_sum_ms"] += latency_ms
        _metrics["requests_harmful"] += harmful_count
        _metrics["requests_safe"] += total - harmful_count


def reset_metrics() -> None:
    """Reset metrics (for testing)."""
    with _metrics_lock:
        _metrics["requests_total"] = 0
        _metrics["requests_harmful"] = 0
        _metrics["requests_safe"] = 0
        _metrics["latency_sum_ms"] = 0.0


def _build_api_key_dependency(expected_key: str | None):
    """Return a FastAPI dependency that enforces X-API-Key when configured."""

    async def _verify(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
        if expected_key is None:
            return
        if x_api_key is None or not _constant_time_eq(x_api_key, expected_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing or invalid X-API-Key",
            )

    return _verify


def _constant_time_eq(a: str, b: str) -> bool:
    """Constant-time string comparison to avoid leaking key length via timing."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a.encode("utf-8"), b.encode("utf-8")):
        result |= x ^ y
    return result == 0


def create_app(config: ServerConfig | None = None) -> "FastAPI":
    """Create FastAPI application."""
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI not installed. Install with: pip install fastapi uvicorn"
        )

    cfg = config or ServerConfig()
    app = FastAPI(
        title="PSG Screening API",
        description="Real-time prompt and response screening for LLM safety",
        version="1.0.0",
    )

    require_api_key = _build_api_key_dependency(cfg.api_key)

    class _RequestSizeLimitMiddleware(BaseHTTPMiddleware):
        """Reject requests with Content-Length over the configured cap.

        We check the header rather than buffering the body so that very large
        payloads are rejected before allocating memory for them.
        """

        def __init__(self, app, max_bytes: int) -> None:
            super().__init__(app)
            self.max_bytes = max_bytes

        async def dispatch(self, request: Request, call_next):
            content_length = request.headers.get("content-length")
            if content_length is not None:
                try:
                    if int(content_length) > self.max_bytes:
                        return JSONResponse(
                            status_code=413,
                            content={"detail": f"request body exceeds {self.max_bytes} bytes"},
                        )
                except ValueError:
                    pass  # malformed header — let FastAPI handle it
            return await call_next(request)

    app.add_middleware(_RequestSizeLimitMiddleware, max_bytes=cfg.max_request_bytes)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Real liveness check — exercises the classifier on a probe input."""
        try:
            classify_response_v2(HEALTH_PROBE_TEXT)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"classifier unavailable: {exc}",
            ) from exc
        return HealthResponse(status="ok", version="1.0.0")

    @app.post("/screen", response_model=ScreenResponse, dependencies=[Depends(require_api_key)])
    async def screen(body: ScreenRequest) -> ScreenResponse:
        """Screen a single text for harmful content."""
        start = time.perf_counter()

        result = classify_response_v2(body.text)
        threshold = body.threshold if body.threshold is not None else cfg.threshold
        harmful = result.harm_score >= threshold and result.attack_successful

        latency_ms = (time.perf_counter() - start) * 1000
        _record_metric(harmful=harmful, latency_ms=latency_ms)

        return ScreenResponse(
            harmful=harmful,
            harm_score=result.harm_score,
            is_refusal=result.is_refusal,
            has_disclaimer=result.has_disclaimer,
            attack_successful=result.attack_successful,
            latency_ms=round(latency_ms, 2),
        )

    @app.post(
        "/screen/bulk",
        response_model=BulkScreenResponse,
        dependencies=[Depends(require_api_key)],
    )
    async def screen_bulk(body: BulkScreenRequest) -> BulkScreenResponse:
        """Screen multiple texts for harmful content."""
        start = time.perf_counter()

        threshold = body.threshold if body.threshold is not None else cfg.threshold
        results: list[ScreenResponse] = []
        harmful_count = 0

        for text in body.texts:
            text_start = time.perf_counter()
            result = classify_response_v2(text)
            harmful = result.harm_score >= threshold and result.attack_successful
            text_latency = (time.perf_counter() - text_start) * 1000

            if harmful:
                harmful_count += 1

            results.append(ScreenResponse(
                harmful=harmful,
                harm_score=result.harm_score,
                is_refusal=result.is_refusal,
                has_disclaimer=result.has_disclaimer,
                attack_successful=result.attack_successful,
                latency_ms=round(text_latency, 2),
            ))

        total_latency = (time.perf_counter() - start) * 1000
        _record_metrics_bulk(
            total=len(body.texts),
            harmful_count=harmful_count,
            latency_ms=total_latency,
        )

        return BulkScreenResponse(
            results=results,
            total=len(results),
            harmful_count=harmful_count,
            latency_ms=round(total_latency, 2),
        )

    @app.get(
        "/metrics",
        response_model=MetricsResponse,
        dependencies=[Depends(require_api_key)],
    )
    async def metrics() -> MetricsResponse:
        """Get server metrics."""
        with _metrics_lock:
            total = _metrics["requests_total"]
            avg_latency = _metrics["latency_sum_ms"] / total if total > 0 else 0.0
            return MetricsResponse(
                requests_total=total,
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
        default=None,
        help="Host to bind to. Default 127.0.0.1; use --allow-public for 0.0.0.0.",
    )
    parser.add_argument(
        "--allow-public",
        action="store_true",
        help="Bind to 0.0.0.0 (all interfaces). Use only on trusted networks.",
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
        "--api-key",
        default=os.getenv("PSG_SERVE_API_KEY"),
        help=(
            "Require this X-API-Key header on /screen, /screen/bulk, /metrics. "
            "Defaults to PSG_SERVE_API_KEY env var if set."
        ),
    )
    parser.add_argument(
        "--max-request-bytes",
        type=int,
        default=MAX_REQUEST_BYTES,
        help=f"Reject requests larger than N bytes (default: {MAX_REQUEST_BYTES})",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    return parser


def _resolve_host(args: argparse.Namespace) -> str:
    if args.host:
        return args.host
    return "0.0.0.0" if args.allow_public else "127.0.0.1"


def main(argv: list[str] | None = None) -> int:
    """Run the server."""
    if not FASTAPI_AVAILABLE:
        print("Error: FastAPI not installed.", file=sys.stderr)
        print("Install with: pip install fastapi uvicorn", file=sys.stderr)
        return 1

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed.", file=sys.stderr)
        print("Install with: pip install uvicorn", file=sys.stderr)
        return 1

    parser = build_parser()
    args = parser.parse_args(argv)

    host = _resolve_host(args)
    config = ServerConfig(
        host=host,
        port=args.port,
        threshold=args.threshold,
        api_key=args.api_key,
        max_request_bytes=args.max_request_bytes,
    )

    auth_state = "ENABLED" if config.api_key else "DISABLED (set --api-key for auth)"
    print(f"Starting PSG server on {config.host}:{config.port}")
    print(f"Default threshold: {config.threshold}")
    print(f"X-API-Key auth: {auth_state}")
    if host == "0.0.0.0":
        print(
            "WARNING: binding to 0.0.0.0 exposes this server on all interfaces.",
            file=sys.stderr,
        )
    print(f"Docs: http://{config.host}:{config.port}/docs")

    app = create_app(config)

    try:
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            reload=args.reload,
        )
    except OSError as exc:
        print(f"Error: failed to bind {config.host}:{config.port}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
