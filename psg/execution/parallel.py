from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from threading import Lock
from typing import Callable

from ..checkpoint import JSONLCheckpoint
from ..llm.client import OpenAICompatibleClient
from ..models import AppConfig, Attack, AttemptResult
from ..security.detectors import Detector

logger = logging.getLogger(__name__)

ProcessAttackFn = Callable[
    [
        AppConfig,
        Attack,
        OpenAICompatibleClient,
        Detector,
        str | None,
    ],
    AttemptResult,
]


class _RateLimiter:
    """Simple token bucket rate limiter for controlling request rate."""

    def __init__(self, rate: float | None) -> None:
        self.rate = rate
        self.lock = Lock()
        self.last_request = 0.0

    def acquire(self) -> None:
        if self.rate is None or self.rate <= 0:
            return

        sleep_time = 0.0
        with self.lock:
            now = time.perf_counter()
            min_interval = 1.0 / self.rate
            next_allowed = self.last_request + min_interval

            if now < next_allowed:
                sleep_time = next_allowed - now
                self.last_request = next_allowed
            else:
                self.last_request = now

        if sleep_time > 0:
            time.sleep(sleep_time)


def _run_attacks_parallel(
    *,
    cfg: AppConfig,
    attacks: list[Attack],
    client: OpenAICompatibleClient,
    checkpoint: JSONLCheckpoint,
    detector: Detector,
    system_prompt: str | None,
    checkpoint_tag: str,
    process_attack_fn: ProcessAttackFn,
) -> list[AttemptResult]:
    results: dict[str, AttemptResult] = {}
    checkpoint_lock = Lock()
    rate_limiter = _RateLimiter(cfg.rate_limit)
    completed = 0
    total = len(attacks)

    def process_one(attack: Attack) -> tuple[str, AttemptResult]:
        nonlocal completed
        rate_limiter.acquire()

        result = process_attack_fn(cfg, attack, client, detector, system_prompt)

        with checkpoint_lock:
            try:
                checkpoint.append({**asdict(result), "mode": checkpoint_tag})
            except Exception:
                logger.exception(
                    "failed to append checkpoint for attack_id=%s mode=%s",
                    attack.id,
                    checkpoint_tag,
                )
            completed += 1
            if completed % 10 == 0 or completed == total:
                logger.info("Progress: %d/%d attacks completed", completed, total)

        return attack.id, result

    workers = min(cfg.workers, len(attacks), 32)
    if workers != cfg.workers:
        logger.warning("Adjusted workers from %d to %d", cfg.workers, workers)

    if cfg.rate_limit:
        logger.info(
            "Running %d attacks with %d workers (rate limit: %.1f req/s)",
            total,
            workers,
            cfg.rate_limit,
        )
    else:
        logger.info("Running %d attacks with %d workers", total, workers)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_one, attack): attack for attack in attacks}

        for future in as_completed(futures):
            attack_id, result = future.result()
            results[attack_id] = result

    return [results[attack.id] for attack in attacks]
