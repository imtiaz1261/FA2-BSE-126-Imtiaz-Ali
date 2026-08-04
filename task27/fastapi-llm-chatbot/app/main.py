"""FastAPI application entrypoint."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import chat, health, metrics
from app.config.settings import get_settings
from app.models.schemas import ErrorResponse, RootResponse
from app.utils.logging import configure_logging, get_logger
from app.utils.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL, uptime_seconds

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Application startup",
        extra={
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "environment": settings.environment,
            "llm_provider": settings.llm_provider,
            "llm_configured": settings.llm_configured(),
        },
    )
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    # Hide interactive docs in production if you prefer; left on here since
    # this endpoint does not expose secrets.
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_and_metrics(request: Request, call_next):
    start = time.perf_counter()
    # Use the route template (e.g. "/chat") rather than the raw path where
    # possible, to keep metric label cardinality bounded.
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        path_label = route.path if route is not None else request.url.path
        status_code = response.status_code if response is not None else 500

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method, path=path_label, status_code=status_code
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, path=path_label).observe(duration)

        logger.info(
            "Request handled",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_seconds": round(duration, 4),
            },
        )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=ErrorResponse(error=str(exc.detail)).model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Request validation failed", extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(error="Invalid request body").model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", extra={"path": request.url.path})
    # Never leak stack traces to clients, especially in production.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(error="Unable to process your request at this time.").model_dump(),
    )


app.include_router(health.router)
app.include_router(chat.router)
app.include_router(metrics.router)


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    return RootResponse(
        application=settings.app_name,
        version=settings.app_version,
        status="running",
    )
