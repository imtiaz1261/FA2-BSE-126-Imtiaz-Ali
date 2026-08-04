import uuid
import hashlib
from datetime import datetime
from benchmark.dataset import QUERIES
from app.services import llm_service, cache_service, prompt_optimizer, cost_tracker
from app.models.database import insert_metric, fetch_metrics
from app.config.settings import get_settings

settings = get_settings()

CONFIGS = {
    "baseline": {"use_cache": False, "optimize_prompt": False},
    "caching": {"use_cache": True, "optimize_prompt": False},
    "prompt_optimization": {"use_cache": False, "optimize_prompt": True},
    "full": {"use_cache": True, "optimize_prompt": True},
}


def _run_one(query: str, use_cache: bool, optimize_prompt: bool, config_label: str):
    prompt_to_send = query
    original_tokens = optimized_tokens = None

    if optimize_prompt:
        opt = prompt_optimizer.optimize_prompt(query)
        prompt_to_send = opt["optimized_prompt"]
        original_tokens = opt["original_tokens"]
        optimized_tokens = opt["optimized_tokens"]

    cache_hit = False
    if use_cache:
        cached = cache_service.get_cached(prompt_to_send, settings.model_name)
        if cached:
            cache_hit = True
            result = cached
        else:
            result = llm_service.call_llm(prompt_to_send)
            cache_service.set_cached(prompt_to_send, settings.model_name, result)
    else:
        result = llm_service.call_llm(prompt_to_send)

    cost = cost_tracker.calculate_cost(
        settings.model_name, result["input_tokens"], result["output_tokens"]
    )

    insert_metric({
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "query_hash": hashlib.sha256(query.encode()).hexdigest()[:16],
        "model": settings.model_name,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "total_tokens": result["total_tokens"],
        "latency_ms": result["latency_ms"],
        "cost_usd": cost["cost_usd"],
        "cache_hit": int(cache_hit),
        "prompt_optimized": int(optimize_prompt),
        "original_prompt_tokens": original_tokens,
        "optimized_prompt_tokens": optimized_tokens,
        "status": result["status"],
        "error": result.get("error"),
        "config_label": config_label,
    })


def run_benchmark(configurations: list[str], repeat_queries: int = 2):
    cache_service.clear_cache()  # start each benchmark run clean

    for config_label in configurations:
        cfg = CONFIGS.get(config_label)
        if not cfg:
            continue
        for query in QUERIES:
            for _ in range(repeat_queries):
                _run_one(query, cfg["use_cache"], cfg["optimize_prompt"], config_label)

    return summarize(configurations)


def summarize(configurations: list[str]):
    report = {}
    for label in configurations:
        rows = [r for r in fetch_metrics() if r["config_label"] == label]
        if not rows:
            continue
        total = len(rows)
        cache_hits = sum(r["cache_hit"] for r in rows)
        latencies = sorted(r["latency_ms"] for r in rows)
        p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0

        report[label] = {
            "requests": total,
            "llm_calls": total - cache_hits,
            "cache_hits": cache_hits,
            "cache_misses": total - cache_hits,
            "cache_hit_rate_pct": round((cache_hits / total) * 100, 2),
            "total_input_tokens": sum(r["input_tokens"] for r in rows),
            "total_output_tokens": sum(r["output_tokens"] for r in rows),
            "total_tokens": sum(r["total_tokens"] for r in rows),
            "avg_latency_ms": round(sum(r["latency_ms"] for r in rows) / total, 2),
            "p95_latency_ms": p95,
            "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
            "avg_cost_per_request_usd": round(sum(r["cost_usd"] for r in rows) / total, 8),
        }

    if "baseline" in report:
        base = report["baseline"]
        for label, r in report.items():
            if label == "baseline":
                r["cost_savings_pct"] = 0.0
                r["latency_improvement_pct"] = 0.0
                continue
            r["cost_savings_pct"] = round(
                (1 - r["total_cost_usd"] / base["total_cost_usd"]) * 100, 2
            ) if base["total_cost_usd"] else 0.0
            r["latency_improvement_pct"] = round(
                (1 - r["avg_latency_ms"] / base["avg_latency_ms"]) * 100, 2
            ) if base["avg_latency_ms"] else 0.0

    return report
