from fastapi import APIRouter
from app.models.database import fetch_metrics
from app.services.cache_service import cache_stats

router = APIRouter()


@router.get("/metrics")
def get_metrics():
    return fetch_metrics()


@router.get("/metrics/summary")
def get_summary():
    rows = fetch_metrics()
    if not rows:
        return {"total_requests": 0}

    total = len(rows)
    cache_hits = sum(r["cache_hit"] for r in rows)
    total_tokens = sum(r["total_tokens"] for r in rows)
    total_cost = sum(r["cost_usd"] for r in rows)
    avg_latency = sum(r["latency_ms"] for r in rows) / total

    return {
        "total_requests": total,
        "total_llm_calls": total - cache_hits,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "avg_latency_ms": round(avg_latency, 2),
        "cache_hit_rate_pct": round((cache_hits / total) * 100, 2),
        "cache_stats": cache_stats(),
    }
