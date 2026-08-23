"""
/conversations and /folders endpoints.

Pagination strategy for GET /conversations: pinned conversations are few by
nature and always shown in full on the first page (unpaginated); everything
else uses keyset pagination on (last_message_at, id) — cheaper and more
consistent under concurrent inserts than OFFSET, which is what actually
matters once a user has 1000+ conversations (see Module 3's frontend spec
for react-window virtualization on top of this).

Search (GET /conversations/search) uses Postgres full-text search across
both `conversations.search_vector` (title) and `messages.search_vector`
(content) — both maintained by DB triggers (see the Alembic migration /
schema.sql), so application code never has to remember to keep them in
sync. Search uses simple OFFSET pagination since result sets are small
relative to the full conversation list.
"""
import base64
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Conversation, Folder, Message, User
from app.schemas_conversations import (
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationMessage,
    ConversationPatchRequest,
    ConversationSummary,
    DateGroup,
    FolderCreateRequest,
    FolderResponse,
    SearchResponse,
    SearchResultItem,
    ShareResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])
folders_router = APIRouter(prefix="/folders", tags=["folders"])

DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100


# ---- Date-group bucketing --------------------------------------------------------
# Buckets are computed against UTC day boundaries. If you need this to match
# the user's local calendar day, pass a client UTC-offset and shift `now`
# before computing boundaries — omitted here to keep the endpoint cacheable
# and timezone-agnostic by default.


def _date_group(ts: datetime, now: datetime) -> DateGroup:
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=7)

    if ts >= today_start:
        return "today"
    if ts >= yesterday_start:
        return "yesterday"
    if ts >= week_start:
        return "previous_7_days"
    return "older"


def _to_summary(c: Conversation, now: datetime) -> ConversationSummary:
    return ConversationSummary(
        id=c.id,
        title=c.title,
        pinned=c.pinned,
        archived=c.archived,
        folder_id=c.folder_id,
        is_shared=c.share_token is not None,
        last_message_at=c.last_message_at,
        created_at=c.created_at,
        date_group=_date_group(c.last_message_at, now),
    )


# ---- Cursor encoding --------------------------------------------------------------
# Opaque to the client by design — base64 JSON so we're free to change the
# shape later without it being treated as a stable public format.


def _encode_cursor(last_message_at: datetime, item_id: uuid.UUID) -> str:
    payload = {"t": last_message_at.isoformat(), "id": str(item_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return datetime.fromisoformat(payload["t"]), uuid.UUID(payload["id"])
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid pagination cursor.")


# ---- List (grouped + paginated) ---------------------------------------------------


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    folder_id: uuid.UUID | None = None,
    archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    items: list[ConversationSummary] = []

    base_filters = [Conversation.user_id == current_user.id, Conversation.archived == archived]
    if folder_id is not None:
        base_filters.append(Conversation.folder_id == folder_id)

    # Pinned items: always in full, only on the first (cursorless) page —
    # they're excluded from every subsequent page so they never repeat.
    if cursor is None:
        pinned_result = await db.execute(
            select(Conversation)
            .where(*base_filters, Conversation.pinned == True)  # noqa: E712
            .order_by(Conversation.last_message_at.desc())
        )
        items.extend(_to_summary(c, now) for c in pinned_result.scalars())

    # Non-pinned, keyset-paginated by (last_message_at, id) both descending.
    non_pinned_filters = [*base_filters, Conversation.pinned == False]  # noqa: E712
    if cursor is not None:
        cursor_ts, cursor_id = _decode_cursor(cursor)
        non_pinned_filters.append(
            or_(
                Conversation.last_message_at < cursor_ts,
                and_(Conversation.last_message_at == cursor_ts, Conversation.id < cursor_id),
            )
        )

    result = await db.execute(
        select(Conversation)
        .where(*non_pinned_filters)
        .order_by(Conversation.last_message_at.desc(), Conversation.id.desc())
        .limit(limit + 1)  # fetch one extra to know whether there's a next page
    )
    rows = list(result.scalars())

    next_cursor = None
    if len(rows) > limit:
        last_kept = rows[limit - 1]
        next_cursor = _encode_cursor(last_kept.last_message_at, last_kept.id)
        rows = rows[:limit]

    items.extend(_to_summary(c, now) for c in rows)
    return ConversationListResponse(items=items, next_cursor=next_cursor)


# ---- Detail (full message history, for reopening from the sidebar) ---------------


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(conversation_id, current_user.id, db)
    await db.refresh(conversation, attribute_names=["messages"])
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        pinned=conversation.pinned,
        archived=conversation.archived,
        folder_id=conversation.folder_id,
        is_shared=conversation.share_token is not None,
        messages=[ConversationMessage.model_validate(m) for m in conversation.messages],
    )


# ---- Create -------------------------------------------------------------------


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.folder_id is not None:
        owned = await db.execute(
            select(Folder).where(Folder.id == payload.folder_id, Folder.user_id == current_user.id)
        )
        if owned.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")

    conversation = Conversation(
        user_id=current_user.id, title=payload.title or "New chat", folder_id=payload.folder_id
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return _to_summary(conversation, datetime.now(timezone.utc))


# ---- Rename / pin / archive / move ------------------------------------------------


async def _get_owned_conversation(
    conversation_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def patch_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationPatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(conversation_id, current_user.id, db)

    if payload.title is not None:
        conversation.title = payload.title
    if payload.pinned is not None:
        conversation.pinned = payload.pinned
    if payload.archived is not None:
        conversation.archived = payload.archived
    if payload.clear_folder:
        conversation.folder_id = None
    elif payload.folder_id is not None:
        owned = await db.execute(
            select(Folder).where(Folder.id == payload.folder_id, Folder.user_id == current_user.id)
        )
        if owned.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")
        conversation.folder_id = payload.folder_id

    await db.commit()
    await db.refresh(conversation)
    return _to_summary(conversation, datetime.now(timezone.utc))


# ---- Delete ---------------------------------------------------------------------


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(conversation_id, current_user.id, db)
    await db.delete(conversation)  # cascades to messages via ondelete="CASCADE"
    await db.commit()


# ---- Search -----------------------------------------------------------------------

_SEARCH_SQL = text(
    """
    WITH q AS (SELECT plainto_tsquery('english', :q) AS query)
    SELECT
        c.id,
        c.title,
        c.pinned,
        c.archived,
        c.folder_id,
        c.share_token,
        c.last_message_at,
        c.created_at,
        GREATEST(
            ts_rank(c.search_vector, q.query),
            COALESCE(MAX(ts_rank(m.search_vector, q.query)), 0)
        ) AS rank,
        (
            SELECT ts_headline(
                'english', m2.content, q.query,
                'MaxFragments=1, MaxWords=24, MinWords=10, ShortWord=3'
            )
            FROM messages m2, q
            WHERE m2.conversation_id = c.id AND m2.search_vector @@ q.query
            ORDER BY ts_rank(m2.search_vector, q.query) DESC
            LIMIT 1
        ) AS message_snippet
    FROM conversations c
    CROSS JOIN q
    LEFT JOIN messages m ON m.conversation_id = c.id AND m.search_vector @@ q.query
    WHERE c.user_id = :user_id
      AND c.archived = :archived
      AND (c.search_vector @@ q.query OR m.search_vector @@ q.query)
    GROUP BY c.id, q.query, c.title
    ORDER BY rank DESC, c.last_message_at DESC
    LIMIT :limit OFFSET :offset
    """
)


@router.get("/search", response_model=SearchResponse)
async def search_conversations(
    q: str = Query(min_length=1, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        _SEARCH_SQL,
        {
            "q": q,
            "user_id": str(current_user.id),
            "archived": archived,
            "limit": limit + 1,
            "offset": offset,
        },
    )
    rows = result.mappings().all()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [
        SearchResultItem(
            id=row["id"],
            title=row["title"],
            pinned=row["pinned"],
            archived=row["archived"],
            folder_id=row["folder_id"],
            is_shared=row["share_token"] is not None,
            last_message_at=row["last_message_at"],
            created_at=row["created_at"],
            date_group=_date_group(row["last_message_at"], now),
            snippet=row["message_snippet"] or row["title"],
        )
        for row in rows
    ]
    next_cursor = str(offset + limit) if has_next else None
    return SearchResponse(items=items, next_cursor=next_cursor)


# ---- Share ------------------------------------------------------------------------


@router.post("/{conversation_id}/share", response_model=ShareResponse)
async def share_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(conversation_id, current_user.id, db)

    # Reuse the existing token if already shared (idempotent — clicking
    # "Share" twice doesn't invalidate a link you already sent someone).
    if conversation.share_token is None:
        conversation.share_token = secrets.token_urlsafe(32)
        conversation.shared_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(conversation)

    return ShareResponse(
        share_token=conversation.share_token,
        share_url=f"{settings.frontend_url}/share/{conversation.share_token}",
        shared_at=conversation.shared_at,
    )


@router.delete("/{conversation_id}/share", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(conversation_id, current_user.id, db)
    conversation.share_token = None
    conversation.shared_at = None
    await db.commit()


# ---- Folders ------------------------------------------------------------------------


@folders_router.get("", response_model=list[FolderResponse])
async def list_folders(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Folder).where(Folder.user_id == current_user.id).order_by(Folder.name)
    )
    return list(result.scalars())


@folders_router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: FolderCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    folder = Folder(user_id=current_user.id, name=payload.name)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


@folders_router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == current_user.id)
    )
    folder = result.scalar_one_or_none()
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")
    # Conversations inside are NOT deleted — their folder_id is cleared via
    # the FK's ON DELETE SET NULL, so they simply fall back to unfiled.
    await db.delete(folder)
    await db.commit()



# ============================================================================
# Memory Extraction Integration
# ============================================================================


@router.post("/{conversation_id}/extract-memories", tags=["memory"])
async def extract_conversation_memories(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract memories from a specific conversation.

    Called after a conversation ends to identify and store durable facts
    for future personalization. This is typically triggered automatically
    via background job, but can be manually invoked as well.

    Args:
        conversation_id: Conversation ID to extract from
        current_user: Authenticated user
        db: Database session

    Returns:
        Extraction results with facts extracted and rejected counts
    """
    try:
        from app.services.memory_extraction_job import MemoryExtractionJob

        job = MemoryExtractionJob()
        log = await job.extract_from_conversation(
            user_id=str(current_user.id),
            conversation_id=conversation_id,
            db=db,
        )

        if not log:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found or extraction failed",
            )

        return {
            "status": "extraction_complete",
            "facts_extracted": log.facts_extracted_count,
            "facts_rejected": log.facts_rejected_count,
            "trigger": log.trigger,
            "success": log.success,
            "error_message": log.error_message,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
