"""
core/exceptions.py — Application-wide exception handlers
========================================================
Provides structured JSON responses for unhandled exceptions and
validation errors. Registered from the FastAPI application factory.
"""

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.logging import get_logger

logger = get_logger(__name__)


async def _handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected exceptions."""
    logger.error("unhandled_exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return a concise validation error response instead of the default HTML."""
    # Convert errors to JSON-serializable format
    errors = []
    for e in exc.errors():
        err = {
            "loc": list(e.get("loc", [])),
            "msg": str(e.get("msg", "")),
            "type": str(e.get("type", "")),
        }
        errors.append(err)
    logger.info("request_validation_error", error_count=len(errors))
    return JSONResponse(
        status_code=422,
        content={"detail": errors, "message": "Request validation failed"},
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Ensure HTTPExceptions are returned as JSON consistently."""
    logger.info("http_exception", status_code=exc.status_code, detail=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_exception_handlers(app) -> None:
    """Attach handlers to a FastAPI app instance."""
    app.add_exception_handler(Exception, _handle_generic_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
