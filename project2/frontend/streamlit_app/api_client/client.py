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

    # ---------------------------------------------------------------
    # RAG / Citations (Phase 9-10)
    # ---------------------------------------------------------------
    def stream_message_with_citations(
        self,
        token: str,
        conversation_id: str,
        content: str,
        mode: str = "Chat",
    ):
        """
        Phase 9/10 streaming variant that also parses the inline
        citation footer appended by the RAG path.

        Yields:
          ("chunk",     text_delta)           — plain text chunk
          ("citations", list[dict])           — citation list (end of stream)
          ("__error__", error_message)        — on failure
        """
        import json
        import re

        url = f"{self.base_url}/conversations/{conversation_id}/messages/stream"
        headers = {"Authorization": f"Bearer {token}"}
        citation_re = re.compile(r"<!--CITATIONS:(\{.*?\})-->", re.DOTALL)

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

                buffer = ""
                for raw_chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if not raw_chunk:
                        continue
                    buffer += raw_chunk
                    # Check for citation footer at the end
                    m = citation_re.search(buffer)
                    if m:
                        # Emit everything before the footer as a text chunk
                        text_before = buffer[: m.start()]
                        if text_before:
                            yield ("chunk", text_before)
                        # Emit citations
                        try:
                            data = json.loads(m.group(1))
                            yield ("citations", data.get("citations", []))
                        except json.JSONDecodeError:
                            pass
                        buffer = buffer[m.end():]
                    else:
                        # Safe to emit everything except the last 50 chars
                        # (the footer could be split across chunks)
                        if len(buffer) > 50:
                            yield ("chunk", buffer[:-50])
                            buffer = buffer[-50:]

                # Flush remaining buffer (no footer found)
                if buffer:
                    yield ("chunk", buffer)

        except requests.exceptions.ConnectionError:
            yield ("__error__", "Can't reach the backend. Is it running?")
        except requests.exceptions.Timeout:
            yield ("__error__", "The backend took too long to respond.")
        except requests.exceptions.RequestException as exc:
            yield ("__error__", f"Unexpected error: {exc}")

    # ---------------------------------------------------------------
    # Agent (Phase 11-12)
    # ---------------------------------------------------------------

    def list_agent_tools(self, token: str) -> ApiResult:
        """Return all available agent tools and their schemas."""
        # We need a real conversation_id here but tools are global;
        # use a placeholder path — the backend ignores the id for this endpoint.
        return self._request("GET", "/conversations/00000000-0000-0000-0000-000000000000/agent/tools", token=token)

    def run_agent(self, token: str, conversation_id: str, content: str) -> ApiResult:
        """Run the agent to completion and return the full JSON result."""
        return self._request(
            "POST",
            f"/conversations/{conversation_id}/agent/run",
            token=token,
            json={"content": content},
            timeout=90,
        )

    def stream_agent(self, token: str, conversation_id: str, content: str):
        """
        Stream agent events as <!--AGENT:{...}--> markers + plain text.

        Yields:
          ("intent",      str)               — intent classification result
          ("tool_call",   dict)              — {name, arguments}
          ("tool_result", dict)              — {name, result}
          ("final",       str)               — final answer text
          ("chunk",       str)               — plain text token
          ("__error__",   str)               — on failure
        """
        import json as _json
        import re

        _AGENT_RE = re.compile(r"<!--AGENT:(\{.*?\})-->", re.DOTALL)

        url = f"{self.base_url}/conversations/{conversation_id}/agent/run/stream"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with requests.post(
                url,
                json={"content": content},
                headers=headers,
                stream=True,
                timeout=90,
            ) as response:
                if response.status_code >= 400:
                    detail = None
                    try:
                        detail = response.json().get("detail")
                    except ValueError:
                        pass
                    yield ("__error__", detail or f"Backend error ({response.status_code}).")
                    return

                buffer = ""
                for raw_chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if not raw_chunk:
                        continue
                    buffer += raw_chunk

                    # Extract all complete AGENT markers from buffer
                    while True:
                        m = _AGENT_RE.search(buffer)
                        if not m:
                            break
                        # Emit any plain text before the marker
                        text_before = buffer[: m.start()].strip()
                        if text_before:
                            yield ("chunk", text_before)
                        # Parse and yield the agent event
                        try:
                            event = _json.loads(m.group(1))
                            ev_type = event.get("type", "")
                            if ev_type == "intent":
                                yield ("intent", event.get("intent", ""))
                            elif ev_type == "tool_call":
                                yield ("tool_call", event)
                            elif ev_type == "tool_result":
                                yield ("tool_result", event)
                            elif ev_type == "final":
                                yield ("final", event.get("answer", ""))
                            elif ev_type == "error":
                                yield ("__error__", event.get("message", "Unknown agent error"))
                        except _json.JSONDecodeError:
                            pass
                        buffer = buffer[m.end():]

                # Flush remaining plain text
                remaining = buffer.strip()
                if remaining:
                    yield ("chunk", remaining)

        except requests.exceptions.ConnectionError:
            yield ("__error__", "Can't reach the backend. Is it running?")
        except requests.exceptions.Timeout:
            yield ("__error__", "The agent took too long to respond.")
        except requests.exceptions.RequestException as exc:
            yield ("__error__", f"Unexpected error: {exc}")

    # ---------------------------------------------------------------
    # Research (Phase 13)
    # ---------------------------------------------------------------
    def run_research(self, token: str, query: str) -> ApiResult:
        """Blocking deep-research run — returns full JSON report."""
        return self._request(
            "POST", "/research/run",
            token=token,
            json={"query": query},
            timeout=180,
        )

    def stream_research(self, token: str, query: str):
        """
        Stream research events as <!--RESEARCH:{...}--> markers.

        Yields:
          ("step",    {"step": str, "detail": str})
          ("sources", list[dict])
          ("report",  {"report": str, "sources": list, "intent": str})
          ("error",   str)
        """
        import json as _json
        import re as _re

        _RE = _re.compile(r"<!--RESEARCH:(\{.*?\})-->", _re.DOTALL)
        url     = f"{self.base_url}/research/stream"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with requests.post(
                url,
                json={"query": query},
                headers=headers,
                stream=True,
                timeout=180,
            ) as response:
                if response.status_code >= 400:
                    detail = None
                    try:
                        detail = response.json().get("detail")
                    except ValueError:
                        pass
                    yield ("error", detail or f"Backend error ({response.status_code}).")
                    return

                buffer = ""
                for raw in response.iter_content(chunk_size=None, decode_unicode=True):
                    if not raw:
                        continue
                    buffer += raw
                    while True:
                        m = _RE.search(buffer)
                        if not m:
                            break
                        try:
                            evt = _json.loads(m.group(1))
                            t   = evt.get("type", "")
                            if t == "step":
                                yield ("step",    evt)
                            elif t == "sources":
                                yield ("sources", evt.get("sources", []))
                            elif t == "report":
                                yield ("report",  evt)
                            elif t == "error":
                                yield ("error",   evt.get("message", "Research failed."))
                        except _json.JSONDecodeError:
                            pass
                        buffer = buffer[m.end():]
        except requests.exceptions.Timeout:
            yield ("error", "Research timed out. Try a more focused query.")
        except requests.exceptions.ConnectionError:
            yield ("error", "Can't reach the backend. Is it running?")
        except requests.exceptions.RequestException as exc:
            yield ("error", f"Unexpected error: {exc}")

    # ---------------------------------------------------------------
    # Subscription & Usage (Phase 15)
    # ---------------------------------------------------------------
    def get_my_usage(self, token: str) -> ApiResult:
        return self._request("GET", "/usage/me", token=token)

    def get_subscription(self, token: str) -> ApiResult:
        return self._request("GET", "/subscription/me", token=token)

    def upgrade_plan(self, token: str, plan: str) -> ApiResult:
        return self._request("POST", "/subscription/upgrade",
                             token=token, json={"plan": plan})

    # ---------------------------------------------------------------
    # Admin (Phase 18)
    # ---------------------------------------------------------------

    def admin_get_stats(self, token: str, days: int = 30) -> ApiResult:
        return self._request("GET", f"/admin/stats?days={days}", token=token)

    def admin_list_users(self, token: str, limit: int = 100, offset: int = 0) -> ApiResult:
        return self._request(
            "GET", f"/admin/users?limit={limit}&offset={offset}", token=token
        )

    def admin_get_user(self, token: str, user_id: str, days: int = 30) -> ApiResult:
        return self._request("GET", f"/admin/users/{user_id}?days={days}", token=token)

    def admin_toggle_active(self, token: str, user_id: str) -> ApiResult:
        return self._request("POST", f"/admin/users/{user_id}/toggle-active", token=token)

    def admin_toggle_admin(self, token: str, user_id: str) -> ApiResult:
        return self._request("POST", f"/admin/users/{user_id}/toggle-admin", token=token)

    def admin_daily_usage(self, token: str, days: int = 30) -> ApiResult:
        return self._request("GET", f"/admin/analytics/usage/daily?days={days}", token=token)

    def admin_endpoint_breakdown(self, token: str, days: int = 30) -> ApiResult:
        return self._request(
            "GET", f"/admin/analytics/usage/endpoints?days={days}", token=token
        )

    def admin_top_users(self, token: str, days: int = 30, limit: int = 10) -> ApiResult:
        return self._request(
            "GET", f"/admin/analytics/usage/top-users?days={days}&limit={limit}", token=token
        )

    def admin_daily_new_users(self, token: str, days: int = 30) -> ApiResult:
        return self._request(
            "GET", f"/admin/analytics/users/daily?days={days}", token=token
        )

    # ── Security analytics (Phase 14) ───────────────────────────────────────
    def admin_security_summary(self, token: str, days: int = 30) -> ApiResult:
        return self._request(
            "GET", f"/admin/analytics/security/summary?days={days}", token=token
        )

    def admin_security_events(self, token: str, limit: int = 50) -> ApiResult:
        return self._request(
            "GET", f"/admin/analytics/security/events?limit={limit}", token=token
        )

    def admin_security_daily(self, token: str, days: int = 30) -> ApiResult:
        return self._request(
            "GET", f"/admin/analytics/security/daily?days={days}", token=token
        )


api_client = ApiClient()
