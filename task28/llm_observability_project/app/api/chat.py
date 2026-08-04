import uuid
import hashlib
from datetime import datetime
from fastapi import APIRouter
from app.models.schemas import ChatRequest, ChatResponse
from app.models.database import insert_metric
from app.services import llm_service, cache_service, prompt_optimizer, cost_tracker, observability
from app.config.settings import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    request_id = str(uuid.uuid4())
    original_prompt_tokens = None
    optimized_prompt_tokens = None
    prompt_to_send = req.message

    if req.optimize_prompt:
        opt = prompt_optimizer.optimize_prompt(req.message)
        prompt_to_send = opt["optimized_prompt"]
        original_prompt_tokens = opt["original_tokens"]
        optimized_prompt_tokens = opt["optimized_tokens"]

    cache_hit = False
    if req.use_cache:
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

    query_hash = hashlib.sha256(req.message.encode()).hexdigest()[:16]

    insert_metric({
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "query_hash": query_hash,
        "model": settings.model_name,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "total_tokens": result["total_tokens"],
        "latency_ms": result["latency_ms"],
        "cost_usd": cost["cost_usd"],
        "cache_hit": int(cache_hit),
        "prompt_optimized": int(req.optimize_prompt),
        "original_prompt_tokens": original_prompt_tokens,
        "optimized_prompt_tokens": optimized_prompt_tokens,
        "status": result["status"],
        "error": result.get("error"),
        "config_label": "live",
    })

    observability.log_trace({
        "query": req.message,
        "response": result["response"],
        "model": settings.model_name,
        "cache_hit": cache_hit,
        "latency_ms": result["latency_ms"],
        "cost_usd": cost["cost_usd"],
    })

    return ChatResponse(
        response=result["response"],
        model=settings.model_name,
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        total_tokens=result["total_tokens"],
        latency_ms=result["latency_ms"],
        estimated_cost_usd=cost["cost_usd"],
        estimated_cost_gbp=cost["cost_gbp"],
        cache_hit=cache_hit,
        prompt_optimized=req.optimize_prompt,
        original_prompt_tokens=original_prompt_tokens,
        optimized_prompt_tokens=optimized_prompt_tokens,
    )
