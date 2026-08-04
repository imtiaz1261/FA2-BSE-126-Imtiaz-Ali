"""
Convenience entrypoint for local development.

Usage:
    python run.py

For production, do NOT use this file — use the Uvicorn/Gunicorn command
documented in the README (no --reload, proper worker count).
"""

import uvicorn

from app.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=not settings.is_production,
    )
