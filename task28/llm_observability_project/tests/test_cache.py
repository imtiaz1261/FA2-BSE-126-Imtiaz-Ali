from unittest.mock import patch
from app.services import cache_service


def test_cache_miss_when_unavailable():
    with patch.object(cache_service, "REDIS_AVAILABLE", False):
        assert cache_service.get_cached("hello", "model") is None


def test_set_cached_noop_when_unavailable():
    with patch.object(cache_service, "REDIS_AVAILABLE", False):
        # Should not raise even though Redis is "down".
        cache_service.set_cached("hello", "model", {"response": "hi"})
