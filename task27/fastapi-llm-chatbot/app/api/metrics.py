"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics() -> Response:
    # generate_latest() only exposes counter/histogram values registered
    # above — never secrets or request content.
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
