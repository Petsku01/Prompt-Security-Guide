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
import sys
import time
from dataclasses import dataclass
from typing import Any

try:
    from fastapi import FastAPI
    from pydantic import BaseModel, Field

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

    # Dummy classes for when FastAPI not installed
    class BaseModel:  # type: ignore[no-redef]
        pass

    def Field(*args, **kwargs):  # type: ignore[no-redef]
        return None


from .security.classifier import classify_response_v2


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    threshold: float = 0.5
    enable_metrics: bool = False


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

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Health check endpoint."""
        from . import __version__

        return HealthResponse(status="ok", version=__version__)

    @app.post("/screen", response_model=ScreenResponse)
    async def screen(body: ScreenRequest) -> ScreenResponse:
        """Screen a single text for harmful content."""
        start = time.perf_counter()

        result = classify_response_v2(body.text)
        threshold = body.threshold if body.threshold is not None else cfg.threshold
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
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
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
    return parser


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

    config = ServerConfig(
        host=args.host,
        port=args.port,
        threshold=args.threshold,
    )

    print(f"Starting PSG server on {config.host}:{config.port}")
    print(f"Default threshold: {config.threshold}")
    print(f"Docs: http://{config.host}:{config.port}/docs")

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
