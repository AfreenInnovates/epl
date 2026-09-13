"""Small bounded TTL cache for repeated provider requests."""

from __future__ import annotations

import copy
import time
from collections import OrderedDict
from collections import deque
from threading import Lock
from typing import Any


class TtlCache:
    """Process-local cache that never grows beyond a fixed number of entries."""

    def __init__(self, max_entries: int = 128, ttl_seconds: int = 300) -> None:
        self.max_entries = max(1, max_entries)
        self.ttl_seconds = max(1, ttl_seconds)
        self._entries: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()

        with self._lock:
            entry = self._entries.get(key)

            if entry is None:
                return None

            created, value = entry
            if now - created >= self.ttl_seconds:
                del self._entries[key]
                return None

            self._entries.move_to_end(key)
            return copy.deepcopy(value)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._entries[key] = (time.monotonic(), copy.deepcopy(value))
            self._entries.move_to_end(key)

            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


class SlidingWindowRateLimiter:
    """Process-local limiter for outbound provider requests."""

    def __init__(self, max_requests: int = 8, window_seconds: int = 60) -> None:
        self.max_requests = max(1, max_requests)
        self.window_seconds = max(1, window_seconds)
        self._requests: deque[float] = deque()
        self._lock = Lock()

    def retry_after(self) -> float | None:
        """Return seconds until the next request is allowed, if currently full."""
        now = time.monotonic()

        with self._lock:
            while self._requests and now - self._requests[0] >= self.window_seconds:
                self._requests.popleft()

            if len(self._requests) < self.max_requests:
                self._requests.append(now)
                return None

            return max(0.1, self.window_seconds - (now - self._requests[0]))
