"""
Typed wrapper around the FastAPI backend.

Every Streamlit page should go through this client instead of calling
`requests` directly, so error handling and base-URL/timeout config
stay in one place. Add one method here per backend endpoint as new
phases land.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

import requests

from config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10


@dataclass
class ApiResult:
    """Uniform result wrapper so callers don't need try/except everywhere."""

    ok: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


class ApiClient:
    def __init__(self, base_url: str | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.base_url = (base_url or settings.API_BASE_URL).rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> ApiResult:
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return ApiResult(ok=True, data=response.json(), status_code=response.status_code)
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to backend at %s", url)
            return ApiResult(ok=False, error="Can't reach the backend. Is it running?")
        except requests.exceptions.Timeout:
            logger.error("Timed out calling %s", url)
            return ApiResult(ok=False, error="The backend took too long to respond.")
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            detail = None
            try:
                detail = exc.response.json().get("detail") if exc.response is not None else None
            except ValueError:
                pass
            logger.error("Backend returned HTTP %s for %s", status, url)
            return ApiResult(ok=False, error=detail or f"Backend error ({status}).", status_code=status)
        except requests.exceptions.RequestException as exc:
            logger.exception("Unexpected error calling %s", url)
            return ApiResult(ok=False, error=f"Unexpected error: {exc}")

    def health_check(self) -> ApiResult:
        return self._request("GET", "/health")


api_client = ApiClient()
