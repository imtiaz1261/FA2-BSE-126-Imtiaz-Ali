"""
Public share endpoint — no authentication. Anyone with a valid share link
can view a read-only, sanitized snapshot of the conversation: title,
messages, and timestamps only. No user identity, internal ids beyond the
conversation's own, pin/archive/folder state, or any other conversation
ever leaks through this endpoint — the response model
(`SharedConversationResponse`) is intentionally a completely separate,
narrower shape than the authenticated `ConversationSummary`/message schemas,
so there's no risk of an unrelated field being added upstream and silently
exposed here.

Mounted at the app root (no `/conversations` prefix, no auth dependency) so
it's reachable as a plain public URL: GET /share/{token}.
"""
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.database import get_db
from app.dependencies import limiter
from app.models import Conversation
from app.schemas_conversations import SharedConversationResponse, SharedMessage

router = APIRouter(prefix="/share", tags=["share"])


@router.get("/{token}", response_model=SharedConversationResponse)
@limiter.limit("30/minute")  # public + unauthenticated: light abuse protection
async def get_shared_conversation(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).where(Conversation.share_token == token)
    )
    conversation = result.scalar_one_or_none()

    # Same 404 whether the token never existed or was revoked — a revoked
    # link should look indistinguishable from one that was never valid.
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This share link is invalid or has been revoked.")

    # Lazy-load messages explicitly (async ORM relationships aren't
    # implicitly awaitable) rather than relying on the lazy relationship.
    await db.refresh(conversation, attribute_names=["messages"])

    return SharedConversationResponse(
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[
            SharedMessage(role=m.role.value, content=m.content, created_at=m.created_at)
            for m in conversation.messages
        ],
    )
