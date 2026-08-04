from fastapi import APIRouter
from app.models.schemas import BenchmarkRequest
from benchmark.runner import run_benchmark

router = APIRouter()


@router.post("/benchmark")
def start_benchmark(req: BenchmarkRequest):
    return run_benchmark(req.configurations, req.repeat_queries)


@router.get("/benchmark/results")
def benchmark_results():
    from app.models.database import fetch_metrics
    return fetch_metrics()
