"""In-process sliding-window rate limiting.

Scope and limitations
---------------------
State lives in this process only. On a multi-replica or serverless deployment
each instance keeps its own counters, so the effective limit is
``limit * instance_count``. That is an accepted trade-off for the current
single-instance deployment and is documented rather than hidden. For a
multi-replica deployment this should be replaced with a shared store
(Redis/Postgres) behind the same interface.

Counters are bounded so a hostile client rotating source IPs cannot grow the
dict without limit.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, status


class _WindowLimiter:
    def __init__(self, max_keys: int = 20_000) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def _prune(self, now: float, window: int) -> None:
        if len(self._hits) <= self._max_keys:
            return
        # Drop keys whose newest hit has aged out, then hard-cap.
        for key in [k for k, q in self._hits.items() if not q or now - q[-1] > window]:
            del self._hits[key]
        while len(self._hits) > self._max_keys:
            self._hits.pop(next(iter(self._hits)))

    def hit(self, bucket: str, key: str, limit: int, window: int) -> bool:
        """Register an attempt. Returns True when the caller is over budget."""
        now = time.monotonic()
        composite = f"{bucket}:{key}"
        with self._lock:
            q = self._hits[composite]
            while q and now - q[0] > window:
                q.popleft()
            q.append(now)
            self._prune(now, window)
            return len(q) > limit

    def failures(self, bucket: str, key: str, window: int) -> int:
        now = time.monotonic()
        composite = f"{bucket}:{key}"
        with self._lock:
            q = self._hits.get(composite)
            if not q:
                return 0
            return sum(1 for t in q if now - t <= window)

    def reset(self, bucket: str, key: str) -> None:
        with self._lock:
            self._hits.pop(f"{bucket}:{key}", None)


class RateLimiter:
    """Thin wrapper that applies the configured policy and raises 429."""

    def __init__(self) -> None:
        self._store = _WindowLimiter()
        self._policy: dict[str, tuple[int, int]] = {}
        self._failure_policy: dict[str, tuple[int, int]] = {}
        from app.core.config import settings

        self.configure(
            settings.LOGIN_RATE_LIMIT_ATTEMPTS,
            settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )

    def configure(self, attempts: int, window_seconds: int) -> None:
        self._policy["login"] = (attempts, window_seconds)
        self._failure_policy["login"] = (attempts, window_seconds)
        # Registration is less critical; give it a separate, looser budget.
        self._policy["register"] = (max(attempts, 5), window_seconds)
        self._failure_policy["register"] = (max(attempts, 5), window_seconds)

    def set_policy(self, bucket: str, limit: int, window_seconds: int) -> None:
        """Set the budget for a bucket.

        A bucket that is not configured gets the default of ten attempts in
        five minutes, which is a login's budget and not necessarily
        anybody else's. An endpoint that needs its own budget says what it
        is.
        """
        self._policy[bucket] = (limit, window_seconds)
        self._failure_policy[bucket] = (limit, window_seconds)

    def check(self, bucket: str, request, key: str) -> None:
        """Raise 429 if this attempt exceeds the budget for ``bucket``."""
        limit, window = self._policy.get(bucket, (10, 300))
        if self._store.hit(bucket, key, limit, window):
            retry_after = window
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many attempts. Please wait before trying again."
                ),
                headers={"Retry-After": str(retry_after)},
            )

    def record_failure(self, bucket: str, key: str) -> None:
        limit, window = self._failure_policy.get(bucket, (10, 300))
        if self._store.failures(bucket, key, window) > limit:
            pass  # budget is enforced on the next `check`

    def reset(self, bucket: str, key: str) -> None:
        self._store.reset(bucket, key)


limiter = RateLimiter()