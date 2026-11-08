import os
import threading
import time
from collections.abc import Callable
from typing import Any


class TTLCache:
    """Tiny in-memory cache: every value expires after `ttl_seconds`."""

    def __init__(self, ttl_seconds: float, max_entries: int = 1000, clock: Callable[[], float] = time.monotonic):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._clock = clock
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= self._clock():
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        if self.ttl_seconds <= 0:  # caching is disabled
            return
        with self._lock:
            if key not in self._data and len(self._data) >= self.max_entries:
                self._data.pop(next(iter(self._data)))  # make room: drop the oldest entry
            self._data[key] = (self._clock() + self.ttl_seconds, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


# Profile responses by user id. 0 disables the cache. Whoever changes a user (US4, US5, ...) must call
# profile_cache.delete(user_id), otherwise the old profile is served until the TTL ends.
profile_cache = TTLCache(ttl_seconds=float(os.getenv("PROFILE_CACHE_TTL_SECONDS", "60")))