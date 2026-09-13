"""Standalone tests for the provider cache."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eplai.rag.cache import SlidingWindowRateLimiter, TtlCache  # noqa: E402


def test_cache_returns_copies_and_expires() -> None:
    cache = TtlCache(max_entries=1, ttl_seconds=1)
    original = {"results": [{"title": "A"}]}
    cache.set("a", original)

    loaded = cache.get("a")
    assert loaded == original
    loaded["results"][0]["title"] = "changed"
    assert cache.get("a")["results"][0]["title"] == "A"

    cache.set("b", {"ok": True})
    assert cache.get("a") is None

    time.sleep(1.05)
    assert cache.get("b") is None


def test_rate_limiter_blocks_until_window_moves() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=1)

    assert limiter.retry_after() is None
    assert limiter.retry_after() is not None

    time.sleep(1.05)
    assert limiter.retry_after() is None


if __name__ == "__main__":
    test_cache_returns_copies_and_expires()
    test_rate_limiter_blocks_until_window_moves()
    print("ok  test_cache_returns_copies_and_expires")
    print("ok  test_rate_limiter_blocks_until_window_moves")
