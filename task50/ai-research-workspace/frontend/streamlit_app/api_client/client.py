"""
Typed wrapper around the FastAPI backend.

Every Streamlit page should go through this client instead of calling
`requests` directly, so error handling, the base URL, and auth headers
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

    def _request(
        self,
        method: str,
        path: str,
        token: Optional[str] = None,
        **kwargs,
    ) -> ApiResult:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {}) or {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = requests.request(method, url, timeout=self.timeout, headers=headers, **kwargs)
            response.raise_for_status()
            data = response.json() if response.content else None
            return ApiResult(ok=True, data=data, status_code=response.status_code)
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

    # ---------------------------------------------------------------
    # Health (Phase 2)
    # ---------------------------------------------------------------
    def health_check(self) -> ApiResult:
        return self._request("GET", "/health")

    # ---------------------------------------------------------------
    # Auth (Phase 4)
    # ---------------------------------------------------------------
    def register(self, email: str, password: str, full_name: str = "") -> ApiResult:
        return self._request(
            "POST",
            "/auth/register",
            json={"email": email, "password": password, "full_name": full_name or None},
        )

    def login(self, email: str, password: str) -> ApiResult:
        return self._request("POST", "/auth/login", json={"email": email, "password": password})

    def me(self, token: str) -> ApiResult:
        return self._request("GET", "/auth/me", token=token)

    # ---------------------------------------------------------------
    # Conversations (Phase 5)
    # ---------------------------------------------------------------
    def list_conversations(self, token: str) -> ApiResult:
        return self._request("GET", "/conversations", token=token)

    def create_conversation(self, token: str, title: str = "New Conversation") -> ApiResult:
        return self._request("POST", "/conversations", token=token, json={"title": title})

    def rename_conversation(self, token: str, conversation_id: str, title: str) -> ApiResult:
        return self._request(
            "PATCH", f"/conversations/{conversation_id}", token=token, json={"title": title}
        )

    def delete_conversation(self, token: str, conversation_id: str) -> ApiResult:
        return self._request("DELETE", f"/conversations/{conversation_id}", token=token)

    # ---------------------------------------------------------------
    # Messages (Phase 6)
    # ---------------------------------------------------------------
    def list_messages(self, token: str, conversation_id: str) -> ApiResult:
        return self._request("GET", f"/conversations/{conversation_id}/messages", token=token)

    def send_message(self, token: str, conversation_id: str, content: str, mode: str = "Chat") -> ApiResult:
        return self._request(
            "POST",
            f"/conversations/{conversation_id}/messages",
            token=token,
            json={"content": content, "mode": mode},
        )

    def stream_message(self, token: str, conversation_id: str, content: str, mode: str = "Chat"):
        """
        Phase 7: yields text chunks as they arrive. Not routed through
        `_request` — streaming needs the raw response object, not a
        parsed ApiResult, and errors are surfaced as a special
        ("__error__", message) tuple so the caller can render them.
        """
        url = f"{self.base_url}/conversations/{conversation_id}/messages/stream"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            with requests.post(
                url,
                json={"content": content, "mode": mode},
                headers=headers,
                stream=True,
                timeout=self.timeout,
            ) as response:
                if response.status_code >= 400:
                    detail = None
                    try:
                        detail = response.json().get("detail")
                    except ValueError:
                        pass
                    yield ("__error__", detail or f"Backend error ({response.status_code}).")
                    return
                for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        yield ("chunk", chunk)
        except requests.exceptions.ConnectionError:
            yield ("__error__", "Can't reach the backend. Is it running?")
        except requests.exceptions.Timeout:
            yield ("__error__", "The backend took too long to respond.")
        except requests.exceptions.RequestException as exc:
            yield ("__error__", f"Unexpected error: {exc}")

    # ---------------------------------------------------------------
    # Documents (Phase 8)
    # ---------------------------------------------------------------
    def list_documents(self, token: str) -> ApiResult:
        return self._request("GET", "/documents", token=token)

    def upload_document(self, token: str, filename: str, content_type: str, file_bytes: bytes) -> ApiResult:
        return self._request(
            "POST",
            "/documents",
            token=token,
            files={"file": (filename, file_bytes, content_type or "application/octet-stream")},
        )

    def delete_document(self, token: str, document_id: str) -> ApiResult:
        return self._request("DELETE", f"/documents/{document_id}", token=token)


api_client = ApiClient()
