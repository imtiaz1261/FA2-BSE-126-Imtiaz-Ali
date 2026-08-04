from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    use_cache: bool = True
    optimize_prompt: bool = True


class ChatResponse(BaseModel):
    response: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    estimated_cost_usd: float
    estimated_cost_gbp: float
    cache_hit: bool
    prompt_optimized: bool
    original_prompt_tokens: Optional[int] = None
    optimized_prompt_tokens: Optional[int] = None


class MetricRecord(BaseModel):
    request_id: str
    timestamp: datetime
    query_hash: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: float
    cache_hit: bool
    prompt_optimized: bool
    original_prompt_tokens: Optional[int] = None
    optimized_prompt_tokens: Optional[int] = None
    status: str
    error: Optional[str] = None


class BenchmarkRequest(BaseModel):
    configurations: list[str] = ["baseline", "caching", "prompt_optimization", "full"]
    repeat_queries: int = 2  # repeats per query so cache hits are measurable
