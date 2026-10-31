from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable

from fastapi import HTTPException, status

from app.core.config import (
    AUTH_RATE_LIMIT_MAX_REQUESTS,
    AUTH_RATE_LIMIT_WINDOW_SECONDS,
    CHAT_RATE_LIMIT_MAX_REQUESTS,
    CHAT_RATE_LIMIT_WINDOW_SECONDS,
)


class InMemoryRateLimiter:
    """Thread-safe fixed-window limiter for a single API worker."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        if max_requests < 1 or window_seconds < 1 or max_keys < 1:
            raise ValueError("Rate-limit settings must be positive.")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._windows: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            self._remove_expired(now)
            window_start, request_count = self._windows.get(
                key, (now, 0)
            )
            if now - window_start >= self.window_seconds:
                window_start, request_count = now, 0

            if request_count >= self.max_requests:
                retry_after = max(
                    1,
                    math.ceil(
                        self.window_seconds - (now - window_start)
                    ),
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

            if key not in self._windows and len(self._windows) >= self._max_keys:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Request protection is temporarily unavailable.",
                )
            self._windows[key] = (window_start, request_count + 1)

    def reset(self) -> None:
        """Clear counters; primarily useful for application/test lifecycle."""
        with self._lock:
            self._windows.clear()

    def _remove_expired(self, now: float) -> None:
        expired_keys = [
            key
            for key, (window_start, _) in self._windows.items()
            if now - window_start >= self.window_seconds
        ]
        for key in expired_keys:
            del self._windows[key]


auth_rate_limiter = InMemoryRateLimiter(
    AUTH_RATE_LIMIT_MAX_REQUESTS,
    AUTH_RATE_LIMIT_WINDOW_SECONDS,
)
chat_rate_limiter = InMemoryRateLimiter(
    CHAT_RATE_LIMIT_MAX_REQUESTS,
    CHAT_RATE_LIMIT_WINDOW_SECONDS,
)
