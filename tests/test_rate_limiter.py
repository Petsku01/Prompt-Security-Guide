"""Tests for the token-bucket rate limiter (Phase 4.3).

The previous min-interval-since-last-call implementation serialized all
workers through one lock, defeating ``--workers > 1`` whenever
``--rate-limit`` was set. These tests pin the new token-bucket behavior:

  * ``rate=None`` / ``rate<=0`` disables limiting (no sleep).
  * A full bucket absorbs a burst of ``capacity`` immediate acquires.
  * Sustained acquires are bounded by ``rate``.
  * Parallel workers collectively see ~rate tokens/s, not rate/workers.
"""
from __future__ import annotations

import threading
import time

from psg.execution.parallel import _RateLimiter


def test_disabled_rate_limit_never_sleeps() -> None:
    rl = _RateLimiter(rate=None)
    start = time.monotonic()
    for _ in range(50):
        rl.acquire()
    assert time.monotonic() - start < 0.05

    rl_zero = _RateLimiter(rate=0)
    start = time.monotonic()
    for _ in range(50):
        rl_zero.acquire()
    assert time.monotonic() - start < 0.05


def test_burst_capacity_lets_initial_calls_pass_without_sleep() -> None:
    # Bucket starts full at capacity=5; 5 immediate acquires should not
    # sleep measurably.
    rl = _RateLimiter(rate=5.0, capacity=5)
    start = time.monotonic()
    for _ in range(5):
        rl.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1, f"burst should not sleep; elapsed={elapsed}"


def test_sustained_rate_is_bounded() -> None:
    # At 10 tokens/s with capacity=1, 5 acquires should take at least
    # (5 - 1) / 10 = 0.4s (the first one consumes the initial token).
    rl = _RateLimiter(rate=10.0, capacity=1)
    start = time.monotonic()
    for _ in range(5):
        rl.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.35, f"rate not enforced; elapsed={elapsed}"
    # Should not take drastically longer than needed.
    assert elapsed < 1.5, f"rate limiter too slow; elapsed={elapsed}"


def test_parallel_workers_share_one_bucket() -> None:
    """N workers at rate R should collectively take ~N/R seconds, not N * 1/R."""
    rate = 20.0
    n = 20
    rl = _RateLimiter(rate=rate, capacity=1)
    barrier = threading.Barrier(n)

    def worker():
        barrier.wait()
        rl.acquire()

    threads = [threading.Thread(target=worker) for _ in range(n)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start

    # Expected: roughly (n - capacity) / rate = 19 / 20 ≈ 0.95s.
    # Allow a wide envelope for CI noise.
    assert elapsed >= 0.5, f"rate not enforced across threads; elapsed={elapsed}"
    assert elapsed < 3.0, f"rate limiter serializes too aggressively; elapsed={elapsed}"


def test_tokens_accumulate_up_to_capacity() -> None:
    # With capacity=3, a brief idle period should let the bucket refill so
    # the next burst of 3 is instant.
    rl = _RateLimiter(rate=10.0, capacity=3)
    rl.acquire()  # consume 1 → 2 tokens left
    time.sleep(0.4)  # bucket refills to capacity (3) again

    start = time.monotonic()
    for _ in range(3):
        rl.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1, f"post-refill burst slept; elapsed={elapsed}"
