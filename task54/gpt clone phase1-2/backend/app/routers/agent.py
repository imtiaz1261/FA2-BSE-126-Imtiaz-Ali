"""
FastAPI routes for Coding Agent functionality.

Endpoints:
- POST /chat/agent - Start agent session with streaming
- POST /agent/changes/{change_id}/approve - Approve a proposed change
- POST /agent/changes/{change_id}/reject - Reject a proposed change
- POST /agent/changes/{change_id}/edit - Edit and re-submit a change
- GET /agent/sessions/{session_id} - Get session status and history
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import Conversation, User
from app.models_agent import (
    AgentPhase,
    AgentSession,
    ChangeStatus,
    ProposedCodeChange,
)
from app.schemas_conversations import ConversationDetailResponse
from app.services.agent_streaming import SSEFormatter, AgentEvents
from app.services.agent_tools import AgentTools
from app.services.docker_sandbox import SandboxConfig, SandboxManager, get_sandbox_manager
from app.services.react_agent import ReactAgent

router = APIRouter(prefix="/agent", tags=["agent"])


# ============================================================================
# Schemas
# ============================================================================


class AgentStartRequest:
    """Request to start agent session."""

    task: str
    repo_path: str
    conversation_id: str
    max_corrections: int = 3


class ChangeApprovalRequest:
    """Request to approve/reject a change."""

    approved: bool
    rejection_reason: Optional[str] = None
    edited_content: Optional[str] = None


# ============================================================================
# Chat Agent Endpoint
# ============================================================================


@router.post("/chat/agent")
async def start_agent_session(
    task: str = Query(..., description="Coding task description"),
    repo_path: str = Query(..., description="Repository path"),
    conversation_id: str = Query(..., description="Conversation ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a coding agent session with streaming.

    Streams agent reasoning, tool calls, and proposed changes as Server-Sent Events.

    Args:
        task: Natural language coding task
        repo_path: Path to repository to work on
        conversation_id: Associated conversation ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        StreamingResponse with SSE events
    """
    try:
        # Validate conversation belongs to user
        conv = await db.scalar(
            select(Conversation).where(
                Conversation.id == uuid.UUID(conversation_id),
                Conversation.user_id == current_user.id,
            )
        )

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Create agent session
        agent_session = AgentSession(
            user_id=current_user.id,
            conversation_id=conv.id,
            task_description=task,
            repo_path=repo_path,
            phase=AgentPhase.planning,
        )
        db.add(agent_session)
        await db.commit()
        await db.refresh(agent_session)

        # Start sandbox
        sandbox_manager = get_sandbox_manager()
        config = SandboxConfig()
        sandbox = await sandbox_manager.create_container(
            str(agent_session.id),
            repo_path,
            config,
        )

        if not sandbox:
            raise Exception("Failed to start sandbox container")

        agent_session.container_id = sandbox.container_id
        await db.commit()

        # Create agent
        tools = AgentTools(repo_path, sandbox)
        # TODO: Inject actual LLM provider
        llm_provider = None

        agent = ReactAgent(agent_session, tools, sandbox, llm_provider)

        # Create streaming response
        async def event_generator():
            try:
                # Run agent
                async for event in agent.run(task, db):
                    yield SSEFormatter.format_event(
                        event.get("type", "unknown"),
                        event,
                    )

                # Cleanup
                await sandbox_manager.destroy_container(str(agent_session.id))

            except Exception as e:
                yield SSEFormatter.format_event(
                    "error",
                    {
                        "message": str(e),
                        "session_id": str(agent_session.id),
                    },
                )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Change Approval Endpoints
# ============================================================================


@router.post("/changes/{change_id}/approve")
async def approve_change(
    change_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a proposed code change."""
    try:
        change_uuid = uuid.UUID(change_id)

        # Fetch change
        change = await db.scalar(
            select(ProposedCodeChange).where(ProposedCodeChange.id == change_uuid)
        )

        if not change:
            raise HTTPException(status_code=404, detail="Change not found")

        # Verify user owns the session
        session = await db.scalar(
            select(AgentSession).where(AgentSession.id == change.session_id)
        )

        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Update change
        change.status = ChangeStatus.approved
        from datetime import datetime
        from sqlalchemy import func

        change.approved_at = func.now()
        await db.commit()

        return {"status": "approved", "change_id": str(change.id)}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/changes/{change_id}/reject")
async def reject_change(
    change_id: str,
    reason: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a proposed code change."""
    try:
        change_uuid = uuid.UUID(change_id)

        change = await db.scalar(
            select(ProposedCodeChange).where(ProposedCodeChange.id == change_uuid)
        )

        if not change:
            raise HTTPException(status_code=404, detail="Change not found")

        session = await db.scalar(
            select(AgentSession).where(AgentSession.id == change.session_id)
        )

        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        change.status = ChangeStatus.rejected
        change.rejection_reason = reason
        from sqlalchemy import func

        change.rejected_at = func.now()
        await db.commit()

        return {"status": "rejected", "change_id": str(change.id)}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/changes/{change_id}/edit")
async def edit_change(
    change_id: str,
    edited_content: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit and re-submit a proposed change."""
    try:
        change_uuid = uuid.UUID(change_id)

        change = await db.scalar(
            select(ProposedCodeChange).where(ProposedCodeChange.id == change_uuid)
        )

        if not change:
            raise HTTPException(status_code=404, detail="Change not found")

        session = await db.scalar(
            select(AgentSession).where(AgentSession.id == change.session_id)
        )

        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        change.user_edit = edited_content
        await db.commit()

        return {"status": "edited", "change_id": str(change.id)}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Session Status Endpoint
# ============================================================================


@router.get("/sessions/{session_id}")
async def get_session_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agent session status and history."""
    try:
        session_uuid = uuid.UUID(session_id)

        session = await db.scalar(
            select(AgentSession).where(
                AgentSession.id == session_uuid,
                AgentSession.user_id == current_user.id,
            )
        )

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Fetch proposed changes
        changes = await db.scalars(
            select(ProposedCodeChange).where(ProposedCodeChange.session_id == session.id)
        )

        return {
            "session_id": str(session.id),
            "phase": session.phase.value,
            "status": session.status,
            "iterations": session.total_iterations,
            "self_corrections": session.self_corrections,
            "changes": [
                {
                    "id": str(c.id),
                    "file": c.file_path,
                    "operation": c.operation,
                    "status": c.status.value,
                    "diff": c.diff,
                }
                for c in changes
            ],
            "summary": session.summary,
            "error": session.error_message,
            "created_at": session.created_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
