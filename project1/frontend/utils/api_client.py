"""
frontend/utils/api_client.py — Centralised HTTP Client
=======================================================
All API calls from the Streamlit frontend go through this class.
It handles auth headers, base URL, error parsing, and SSE streaming.
"""

from __future__ import annotations
import os
from typing import Generator, Optional
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class APIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class APIClient:
    def __init__(self, base_url: str = BACKEND_URL, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _raise(self, r: httpx.Response):
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise APIError(r.status_code, str(detail))

    # ── Auth ──────────────────────────────────────────────────────────

    def register(self, full_name: str, email: str, password: str, confirm_password: str) -> dict:
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{self.base_url}/api/v1/auth/register", json={
                "full_name": full_name, "email": email,
                "password": password, "confirm_password": confirm_password,
            })
            self._raise(r)
            return r.json()

    def login(self, email: str, password: str) -> dict:
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{self.base_url}/api/v1/auth/login",
                       json={"email": email, "password": password})
            self._raise(r)
            return r.json()

    def logout(self, refresh_token: str) -> None:
        with httpx.Client(timeout=10) as c:
            c.post(f"{self.base_url}/api/v1/auth/logout",
                   json={"refresh_token": refresh_token},
                   headers=self._headers())

    def get_me(self) -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{self.base_url}/api/v1/auth/me", headers=self._headers())
            self._raise(r)
            return r.json()

    def update_profile(self, full_name: str) -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.patch(f"{self.base_url}/api/v1/auth/me",
                        json={"full_name": full_name}, headers=self._headers())
            self._raise(r)
            return r.json()

    def change_password(self, current_password: str, new_password: str, confirm: str) -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.post(f"{self.base_url}/api/v1/auth/me/password", json={
                "current_password": current_password,
                "new_password": new_password,
                "confirm_new_password": confirm,
            }, headers=self._headers())
            self._raise(r)
            return r.json()

    # ── Chat ─────────────────────────────────────────────────────────

    def stream_chat(self, message: str, conversation_id: Optional[str] = None,
                    mode: str = "chat") -> Generator[str, None, None]:
        """Yield SSE data lines from the streaming chat endpoint."""
        payload = {"message": message, "mode": mode}
        if conversation_id:
            payload["conversation_id"] = conversation_id
        with httpx.Client(timeout=120) as c:
            with c.stream("POST", f"{self.base_url}/api/v1/chat/stream",
                          json=payload, headers=self._headers()) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        yield line[6:]

    def stream_agent(self, message: str, conversation_id: Optional[str] = None) -> Generator[str, None, None]:
        payload = {"message": message, "mode": "agent"}
        if conversation_id:
            payload["conversation_id"] = conversation_id
        with httpx.Client(timeout=180) as c:
            with c.stream("POST", f"{self.base_url}/api/v1/chat/agent/stream",
                          json=payload, headers=self._headers()) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        yield line[6:]

    def list_conversations(self, search: str = None) -> dict:
        params = {}
        if search:
            params["search"] = search
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{self.base_url}/api/v1/chat/conversations",
                      params=params, headers=self._headers())
            self._raise(r)
            return r.json()

    def get_conversation_messages(self, conv_id: str) -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{self.base_url}/api/v1/chat/conversations/{conv_id}",
                      headers=self._headers())
            self._raise(r)
            return r.json()

    def create_conversation(self, title: str = "New Conversation", feature: str = "chat") -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.post(f"{self.base_url}/api/v1/chat/conversations",
                       json={"title": title, "feature": feature}, headers=self._headers())
            self._raise(r)
            return r.json()

    def rename_conversation(self, conv_id: str, title: str) -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.patch(f"{self.base_url}/api/v1/chat/conversations/{conv_id}",
                        json={"title": title}, headers=self._headers())
            self._raise(r)
            return r.json()

    def delete_conversation(self, conv_id: str) -> None:
        with httpx.Client(timeout=10) as c:
            c.delete(f"{self.base_url}/api/v1/chat/conversations/{conv_id}",
                     headers=self._headers())

    # ── Documents ────────────────────────────────────────────────────

    def upload_document(self, file_bytes: bytes, filename: str, mime_type: str) -> dict:
        with httpx.Client(timeout=60) as c:
            r = c.post(f"{self.base_url}/api/v1/documents/upload",
                       files={"file": (filename, file_bytes, mime_type)},
                       headers={"Authorization": f"Bearer {self.token}"})
            self._raise(r)
            return r.json()

    def list_documents(self, search: str = None) -> dict:
        params = {}
        if search:
            params["search"] = search
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{self.base_url}/api/v1/documents/",
                      params=params, headers=self._headers())
            self._raise(r)
            return r.json()

    def get_document_status(self, doc_id: str) -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{self.base_url}/api/v1/documents/{doc_id}",
                      headers=self._headers())
            self._raise(r)
            return r.json()

    def delete_document(self, doc_id: str) -> None:
        with httpx.Client(timeout=10) as c:
            c.delete(f"{self.base_url}/api/v1/documents/{doc_id}",
                     headers=self._headers())

    def query_documents(self, question: str, mode: str = "hybrid", top_k: int = 5) -> dict:
        with httpx.Client(timeout=60) as c:
            r = c.post(f"{self.base_url}/api/v1/documents/query",
                       json={"question": question, "mode": mode, "top_k": top_k},
                       headers=self._headers())
            self._raise(r)
            return r.json()

    # ── Subscriptions ────────────────────────────────────────────────

    def get_plans(self) -> list:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{self.base_url}/api/v1/subscriptions/plans")
            self._raise(r)
            return r.json()

    def get_my_subscription(self) -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{self.base_url}/api/v1/subscriptions/me", headers=self._headers())
            self._raise(r)
            return r.json()

    def get_usage(self) -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{self.base_url}/api/v1/subscriptions/usage", headers=self._headers())
            self._raise(r)
            return r.json()

    def upgrade_plan(self, plan: str) -> dict:
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{self.base_url}/api/v1/subscriptions/upgrade",
                       json={"plan": plan}, headers=self._headers())
            self._raise(r)
            return r.json()

    def cancel_subscription(self) -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.post(f"{self.base_url}/api/v1/subscriptions/cancel", headers=self._headers())
            self._raise(r)
            return r.json()

    # ── Admin ────────────────────────────────────────────────────────

    def admin_list_users(self, page: int = 1, search: str = None) -> dict:
        params = {"page": page, "page_size": 20}
        if search:
            params["search"] = search
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{self.base_url}/api/v1/admin/users",
                      params=params, headers=self._headers())
            self._raise(r)
            return r.json()

    def admin_user_action(self, user_id: str, action: str) -> dict:
        with httpx.Client(timeout=10) as c:
            r = c.post(f"{self.base_url}/api/v1/admin/users/{user_id}/action",
                       json={"action": action}, headers=self._headers())
            self._raise(r)
            return r.json()

    def admin_usage_metrics(self) -> dict:
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{self.base_url}/api/v1/admin/metrics/usage", headers=self._headers())
            self._raise(r)
            return r.json()

    def admin_subscription_metrics(self) -> dict:
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{self.base_url}/api/v1/admin/metrics/subscriptions", headers=self._headers())
            self._raise(r)
            return r.json()

    def admin_system_health(self) -> dict:
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{self.base_url}/api/v1/admin/health", headers=self._headers())
            self._raise(r)
            return r.json()
