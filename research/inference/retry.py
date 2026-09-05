"""Backoff retry for transient sampling failures (429/5xx/timeouts).

High concurrency is the standing policy; this makes it safe: a rate-limit
burst becomes a short delay instead of a lost attempt. Non-transient errors
re-raise immediately — genuine failures must stay visible to the cascade's
health logic, not be retried into ambiguity.
"""

import asyncio
import random

TRANSIENT_MARKERS = ("429", "Too many requests", "rate limit", "RateLimit", "timeout", "Timeout",
                     "502", "503", "504", "Service Unavailable", "overloaded", "Connection",
                     "InternalServerError", "temporarily")


def is_transient(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}"
    return any(marker in text for marker in TRANSIENT_MARKERS)


async def with_backoff(coro_fn, *, tries: int = 4, base_seconds: float = 2.0):
    """coro_fn: zero-arg callable returning a fresh coroutine per attempt."""
    for attempt in range(tries):
        try:
            return await coro_fn()
        except Exception as e:
            if attempt == tries - 1 or not is_transient(e):
                raise
            await asyncio.sleep(base_seconds * (2 ** attempt) * (0.5 + random.random()))
