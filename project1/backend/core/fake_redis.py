"""
backend/core/fake_redis.py — In-memory Redis fallback for dev mode
===================================================================
Used when Redis is not installed/running and APP_ENV != "production".

Implements only the subset of the Redis API that this application uses:
    setex(key, ttl, value)
    get(key)
    exists(*keys)
    delete(*keys)
    ping()

Token blacklisting still works — it's all in-process memory.
Caveat: state is lost on restart, and is NOT shared across workers.
That's fine for local single-process development.
"""
import threading
import time
from typing import Optional


class FakeRedis:
    """
    Thread-safe in-memory Redis stub.
    Supports TTL-based expiry checked on every read.
    """

    def __init__(self):
        self._store: dict[str, tuple[str, Optional[float]]] = {}
        # (value, expire_at_unix) — expire_at=None means no expiry
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_alive(self, key: str) -> bool:
        if key not in self._store:
            return False
        _, expire_at = self._store[key]
        if expire_at is not None and time.time() > expire_at:
            del self._store[key]
            return False
        return True

    # ------------------------------------------------------------------
    # Public API (async to match aioredis interface)
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        return True

    async def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        with self._lock:
            self._store[key] = (str(value), time.time() + ttl_seconds)

    async def get(self, key: str) -> Optional[str]:
        with self._lock:
            if not self._is_alive(key):
                return None
            return self._store[key][0]

    async def exists(self, *keys: str) -> int:
        with self._lock:
            return sum(1 for k in keys if self._is_alive(k))

    async def delete(self, *keys: str) -> int:
        with self._lock:
            deleted = 0
            for k in keys:
                if k in self._store:
                    del self._store[k]
                    deleted += 1
            return deleted

    async def aclose(self) -> None:
        pass

    # Make it work as an async context manager
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# Module-level singleton — shared for the entire process lifetime
_instance: Optional[FakeRedis] = None


def get_fake_redis() -> FakeRedis:
    global _instance
    if _instance is None:
        _instance = FakeRedis()
    return _instance
