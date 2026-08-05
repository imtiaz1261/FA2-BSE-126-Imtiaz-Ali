"""
Messages router — Phase 6/7/9/10/11/17/14/15.

Phase 14 additions:
  - Input guard runs BEFORE every LLM call (blocks prompt injection, jailbreak, etc.)
  - RAG guard sanitises retrieved chunks before context injection
  - Output guard redacts PII and blocks dangerous replies
  - Security events written to DB for every blocked request

Phase 15 additions:
  - Monthly quota enforced before processing (429 if exceeded)
"""

import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.message import MessageRole
from app.models.user import User
from app.schemas.message import MessageCreate, MessageOut
from app.services import conversation_service, message_service, prompts
from app.services.hybrid_retrieval import hybrid_retrieve
from app.services.llm_service import LLMServiceError, chat_completion, stream_chat_completion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["messages"])

_RAG_MODE   = "Knowledge (RAG)"
_AGENT_MODE = "Agent"


def _get_owned_conversation(db: Session, current_user: User, conversation_id: uuid.UUID):
    conversation = conversation_service.get_conversation(db, current_user.id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


# ── quota enforcement helper ──────────────────────────────────────────────────

def _enforce_quota(db: Session, user: User, endpoint: str = "messages") -> None:
    """Raise HTTP 429 if the user has exceeded their monthly plan limit."""
    try:
        from app.services.subscription_service import check_quota
        ok, msg = check_quota(db, user)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=msg,
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Quota check failed (non-fatal): %s", exc)


# ── guardrail helpers ─────────────────────────────────────────────────────────

async def _run_input_guard(
    text: str,
    db: Session,
    user_id: uuid.UUID,
    endpoint: str,
) -> None:
    """Run input guardrail; raise HTTP 400 with structured message if blocked."""
    try:
        from app.guardrails.input_guard import check_input
        from app.services.security_service import log_security_event

        result = await check_input(text)
        if result.blocked:
            log_security_event(
                db,
                category=result.category,
                severity=result.severity,
                action="blocked",
                reason=result.reason,
                input_snippet=text[:200],
                endpoint=endpoint,
                user_id=user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "blocked": True,
                    "category": result.category,
                    "severity": result.severity,
                    "reason": result.reason,
                    "message": (
                        "Your request was blocked by the AI Security Pipeline. "
                        f"Reason: {result.reason}. Please modify your request and try again."
                    ),
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Input guard error (non-fatal): %s", exc)


async def _run_output_guard(
    text: str,
    db: Session,
    user_id: uuid.UUID,
    endpoint: str,
) -> str:
    """Run output guardrail; returns sanitised text or raises HTTP 502 if dangerous."""
    try:
        from app.guardrails.output_guard import check_output
        from app.services.security_service import log_security_event

        result = await check_output(text)
        if not result.clean:
            log_security_event(
                db,
                category="dangerous_output",
                severity="high",
                action="blocked",
                reason=result.detail,
                input_snippet=text[:200],
                endpoint=endpoint,
                user_id=user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI response was blocked by the output security filter.",
            )
        if result.issue == "pii_redacted":
            log_security_event(
                db,
                category="pii_redacted",
                severity="medium",
                action="sanitised",
                reason=result.detail,
                endpoint=endpoint,
                user_id=user_id,
            )
        return result.sanitised
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Output guard error (non-fatal): %s", exc)
        return text


def _sanitise_rag_chunks(chunks: list) -> list:
    """Sanitise RAG chunks via the RAG guardrail."""
    try:
        from app.guardrails.rag_guard import sanitise_chunks
        return sanitise_chunks(chunks)
    except Exception as exc:
        logger.warning("RAG guard error (non-fatal): %s", exc)
        return chunks


# ─────────────────────────────────────────────────────────────────────────────
# GET — list messages
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[MessageOut])
def list_messages(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageOut]:
    _get_owned_conversation(db, current_user, conversation_id)
    msgs = message_service.list_messages(db, conversation_id)
    return [MessageOut.model_validate(m) for m in msgs]


# ─────────────────────────────────────────────────────────────────────────────
# POST — non-streaming
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    _get_owned_conversation(db, current_user, conversation_id)

    # ── Phase 15: Quota check ─────────────────────────────────────────────────
    _enforce_quota(db, current_user, endpoint="messages")

    # ── Phase 14: Input guard ─────────────────────────────────────────────────
    await _run_input_guard(data.content, db, current_user.id, "send_message")

    history = message_service.list_messages(db, conversation_id)
    message_service.add_message(db, conversation_id, MessageRole.USER, data.content)

    # ── Langfuse trace ────────────────────────────────────────────────────────
    from app.services.langfuse_service import (
        create_trace, finish_span, flush, get_langfuse, start_span,
    )
    lf = get_langfuse()
    trace = create_trace(
        lf,
        name=f"message:{data.mode.lower().replace(' ', '-')}",
        user_id=str(current_user.id),
        session_id=str(conversation_id),
        metadata={"mode": data.mode},
        tags=[data.mode],
    )

    # ── Agent mode ────────────────────────────────────────────────────────────
    if data.mode == _AGENT_MODE:
        from app.agents.executor import run_agent
        agent_span = start_span(trace, "agent-run")
        t0 = time.monotonic()
        result = await run_agent(
            user_message=data.content,
            user_id=current_user.id,
            conversation_id=conversation_id,
            history=history, db=db,
        )
        finish_span(agent_span, output=result.final_answer[:300],
                    metadata={"latency_ms": int((time.monotonic()-t0)*1000)})
        flush(lf)
        # Output guard on agent answer
        safe_answer = await _run_output_guard(
            result.final_answer, db, current_user.id, "agent"
        )
        full_content = safe_answer
        if result.tool_results:
            full_content += _format_tool_summary(result.tool_results)
        assistant_message = message_service.add_message(
            db, conversation_id, MessageRole.ASSISTANT, full_content
        )
        _record_usage(db, current_user.id, data.mode, full_content, [])
        return MessageOut.model_validate(assistant_message)

    # ── RAG path ──────────────────────────────────────────────────────────────
    if data.mode == _RAG_MODE:
        rag_span = start_span(trace, "rag-retrieval")
        try:
            chunks = await hybrid_retrieve(db=db, user_id=current_user.id, query=data.content)
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)
            chunks = []
        # Phase 14: sanitise chunks
        chunks = _sanitise_rag_chunks(chunks)
        finish_span(rag_span, output=f"{len(chunks)} chunks")
        llm_messages = prompts.build_rag_messages(history, data.content, chunks)
    else:
        chunks       = []
        llm_messages = prompts.build_messages(history, data.content, data.mode)

    # ── LLM call ──────────────────────────────────────────────────────────────
    try:
        reply_text = await chat_completion(
            llm_messages, trace=trace, generation_name="llm-reply",
            user_id=str(current_user.id),
        )
    except LLMServiceError as exc:
        flush(lf)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    flush(lf)

    # ── Phase 14: Output guard ────────────────────────────────────────────────
    reply_text = await _run_output_guard(reply_text, db, current_user.id, "send_message")

    _record_usage(db, current_user.id, data.mode, reply_text, llm_messages)

    citations    = prompts.extract_citations(reply_text, chunks) if chunks else []
    full_content = _attach_citations(reply_text, citations)

    assistant_message = message_service.add_message(
        db, conversation_id, MessageRole.ASSISTANT, full_content
    )
    return MessageOut.model_validate(assistant_message)


# ─────────────────────────────────────────────────────────────────────────────
# POST /stream — streaming
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/stream")
async def stream_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    _get_owned_conversation(db, current_user, conversation_id)

    # Phase 15: quota
    _enforce_quota(db, current_user, "stream_message")

    # Phase 14: input guard
    await _run_input_guard(data.content, db, current_user.id, "stream_message")

    history = message_service.list_messages(db, conversation_id)
    message_service.add_message(db, conversation_id, MessageRole.USER, data.content)

    from app.services.langfuse_service import (
        create_trace, finish_span, flush, get_langfuse, start_span,
    )
    lf = get_langfuse()
    trace = create_trace(
        lf,
        name=f"stream:{data.mode.lower().replace(' ', '-')}",
        user_id=str(current_user.id),
        session_id=str(conversation_id),
        metadata={"mode": data.mode},
        tags=[data.mode, "stream"],
    )

    # ── Agent streaming ───────────────────────────────────────────────────────
    if data.mode == _AGENT_MODE:
        from app.agents.executor import stream_agent
        from app.agents.streaming import format_event

        async def agent_generator():
            final_text = ""
            tool_results_seen = []
            try:
                async for event in stream_agent(
                    user_message=data.content,
                    user_id=current_user.id,
                    conversation_id=conversation_id,
                    history=history, db=db,
                ):
                    yield format_event(event) + "\n"
                    if event.get("type") == "final":
                        final_text = event.get("answer", "")
                    if event.get("type") == "tool_result":
                        tool_results_seen.append(event)
            except Exception as exc:
                yield format_event({"type": "error", "message": str(exc)}) + "\n"
            finally:
                flush(lf)
                if final_text:
                    safe = await _run_output_guard(final_text, db, current_user.id, "agent-stream")
                    summary   = _format_tool_summary(tool_results_seen) if tool_results_seen else ""
                    persisted = safe + summary
                    message_service.add_message(db, conversation_id, MessageRole.ASSISTANT, persisted)
                    _record_usage(db, current_user.id, data.mode, persisted, [])

        return StreamingResponse(agent_generator(), media_type="text/plain")

    # ── RAG streaming ─────────────────────────────────────────────────────────
    if data.mode == _RAG_MODE:
        rag_span = start_span(trace, "rag-retrieval-stream")
        try:
            chunks = await hybrid_retrieve(db=db, user_id=current_user.id, query=data.content)
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)
            chunks = []
        chunks = _sanitise_rag_chunks(chunks)
        finish_span(rag_span, output=f"{len(chunks)} chunks")
        llm_messages = prompts.build_rag_messages(history, data.content, chunks)
    else:
        chunks       = []
        llm_messages = prompts.build_messages(history, data.content, data.mode)

    async def event_generator():
        collected: list[str] = []
        try:
            async for chunk in stream_chat_completion(
                llm_messages, trace=trace, generation_name="llm-stream"
            ):
                collected.append(chunk)
                yield chunk
        except LLMServiceError as exc:
            yield f"\n\n[Error: {exc}]"
        finally:
            full_text = "".join(collected).strip()
            flush(lf)
            if full_text:
                # Output guard
                full_text = await _run_output_guard(
                    full_text, db, current_user.id, "stream_message"
                )
                _record_usage(db, current_user.id, data.mode, full_text, llm_messages)
                citations = prompts.extract_citations(full_text, chunks) if chunks else []
                if citations:
                    yield f"\n\n<!--CITATIONS:{json.dumps({'citations': citations})}-->"
                    full_text = _attach_citations(full_text, citations)
                message_service.add_message(
                    db, conversation_id, MessageRole.ASSISTANT, full_text
                )

    return StreamingResponse(event_generator(), media_type="text/plain")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _attach_citations(reply_text: str, citations: list[dict]) -> str:
    if not citations:
        return reply_text
    lines = ["\n\n---\n**Sources:**"]
    for c in citations:
        page = f", p. {c['page_number']}" if c.get("page_number") else ""
        lines.append(f"- {c['ref']} {c['document_name']}{page}")
    return reply_text + "\n".join(lines)


def _format_tool_summary(tool_results: list) -> str:
    if not tool_results:
        return ""
    lines = ["\n\n---\n**Tools used:**"]
    for tr in tool_results:
        lines.append(f"- **{tr.get('name','?')}**: {str(tr.get('result',''))[:120]}")
    return "\n".join(lines)


def _record_usage(db, user_id, mode, reply_text, input_messages) -> None:
    try:
        from app.core.config import settings
        from app.services.usage_service import estimate_cost, record_usage
        input_chars  = sum(len(str(m.get("content", ""))) for m in input_messages)
        output_chars = len(reply_text)
        p = max(1, input_chars  // 4)
        o = max(1, output_chars // 4)
        cost = estimate_cost(settings.LLM_MODEL, p, o)
        endpoint_map = {
            "Chat": "chat", "Knowledge (RAG)": "rag",
            "Agent": "agent", "Research": "research",
        }
        record_usage(db, user_id, endpoint_map.get(mode, mode.lower()), p + o, cost)
    except Exception as exc:
        logger.warning("Usage recording failed: %s", exc)
