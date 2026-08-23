"""Pydantic request/response schemas for /conversations, /folders, and the
public /share endpoint.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DateGroup = Literal["today", "yesterday", "previous_7_days", "older"]


# ---- Folders ------------------------------------------------------------------


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Conversations --------------------------------------------------------------


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New chat", max_length=255)
    folder_id: uuid.UUID | None = None


class ConversationPatchRequest(BaseModel):
    """All fields optional — PATCH only touches what's provided.
    Used for rename (title), pin/unpin, archive/unarchive, and moving
    between folders (folder_id: null clears the folder).
    """

    title: str | None = Field(default=None, min_length=1, max_length=255)
    pinned: bool | None = None
    archived: bool | None = None
    folder_id: uuid.UUID | None = Field(default=None)
    clear_folder: bool = False  # set true to explicitly move OUT of a folder


class ConversationSummary(BaseModel):
    """List/search item — no message bodies, keeps the sidebar payload light."""

    id: uuid.UUID
    title: str
    pinned: bool
    archived: bool
    folder_id: uuid.UUID | None
    is_shared: bool
    last_message_at: datetime
    created_at: datetime
    date_group: DateGroup

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    items: list[ConversationSummary]
    next_cursor: str | None  # opaque cursor for the next page, null when exhausted


class SearchResultItem(ConversationSummary):
    """Adds a short snippet showing where the match was found."""

    snippet: str


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    next_cursor: str | None


class ShareResponse(BaseModel):
    share_token: str
    share_url: str
    shared_at: datetime


# ---- Full conversation detail (authenticated) ------------------------------------


class ConversationMessage(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    """Returned by GET /conversations/{id} — the full message history for
    reopening a past conversation from the sidebar."""

    id: uuid.UUID
    title: str
    pinned: bool
    archived: bool
    folder_id: uuid.UUID | None
    is_shared: bool
    messages: list[ConversationMessage]


# ---- Public, read-only share view -----------------------------------------------


class SharedMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class SharedConversationResponse(BaseModel):
    """Sanitized: no user_id, no internal ids beyond the conversation's own,
    no folder/pin/archive state — just what a read-only viewer should see.
    """

    title: str
    created_at: datetime
    messages: list[SharedMessage]
