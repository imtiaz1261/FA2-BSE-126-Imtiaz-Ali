import hashlib
import json
import redis
from app.config.settings import get_settings

settings = get_settings()

try:
    _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    _redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    _redis_client = None
    REDIS_AVAILABLE = False


def make_cache_key(message: str, model: str) -> str:
    raw = f"{model}:{message.strip().lower()}"
    return "llmcache:" + hashlib.sha256(raw.encode()).hexdigest()


def get_cached(message: str, model: str) -> dict | None:
    if not REDIS_AVAILABLE:
        return None
    try:
        key = make_cache_key(message, model)
        val = _redis_client.get(key)
        return json.loads(val) if val else None
    except Exception:
        # Redis flaked mid-request — degrade gracefully, don't break the chat.
        return None


def set_cached(message: str, model: str, payload: dict):
    if not REDIS_AVAILABLE:
        return
    try:
        key = make_cache_key(message, model)
        _redis_client.setex(key, settings.cache_ttl_seconds, json.dumps(payload))
    except Exception:
        pass


def cache_stats() -> dict:
    if not REDIS_AVAILABLE:
        return {"available": False}
    try:
        keys = _redis_client.keys("llmcache:*")
        return {"available": True, "cached_entries": len(keys)}
    except Exception:
        return {"available": False}


def clear_cache():
    if not REDIS_AVAILABLE:
        return 0
    keys = _redis_client.keys("llmcache:*")
    if keys:
        _redis_client.delete(*keys)
    return len(keys)
