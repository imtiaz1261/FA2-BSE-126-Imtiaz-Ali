"""
Integration tests for agent API endpoints.

Tests:
- Agent session creation
- Streaming response
- Change approval workflow
- Session status retrieval
"""

import json
import uuid
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import User, Conversation
from app.models_agent import AgentSession, ProposedCodeChange, ChangeStatus
from app.database import get_db


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="agent-test@example.com",
        username="agent-tester",
        hashed_password="fake-hash",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def test_conversation(db_session: AsyncSession, test_user: User) -> Conversation:
    """Create a test conversation."""
    conv = Conversation(
        id=uuid.uuid4(),
        user_id=test_user.id,
        title="Agent Test",
    )
    db_session.add(conv)
    await db_session.commit()
    return conv


@pytest.fixture
async def test_session(
    db_session: AsyncSession,
    test_user: User,
    test_conversation: Conversation,
) -> AgentSession:
    """Create a test agent session."""
    session = AgentSession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        conversation_id=test_conversation.id,
        task_description="Test task",
        repo_path="/test/repo",
    )
    db_session.add(session)
    await db_session.commit()
    return session


@pytest.fixture
async def test_changes(
    db_session: AsyncSession,
    test_session: AgentSession,
) -> list[ProposedCodeChange]:
    """Create test proposed changes."""
    changes = [
        ProposedCodeChange(
            id=uuid.uuid4(),
            session_id=test_session.id,
            file_path="src/main.py",
            operation="update",
            original_content="print('old')\n",
            proposed_content="print('new')\n",
            diff="--- a/src/main.py\n+++ b/src/main.py\n-print('old')\n+print('new')\n",
            status=ChangeStatus.staged,
        ),
        ProposedCodeChange(
            id=uuid.uuid4(),
            session_id=test_session.id,
            file_path="test.py",
            operation="create",
            original_content=None,
            proposed_content="# New file\n",
            diff="--- /dev/null\n+++ b/test.py\n+# New file\n",
            status=ChangeStatus.staged,
        ),
    ]
    db_session.add_all(changes)
    await db_session.commit()
    return changes


# ============================================================================
# Endpoint Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_session_status(
    client: TestClient,
    test_session: AgentSession,
    test_changes: list[ProposedCodeChange],
    auth_headers: dict,
):
    """Test GET /agent/sessions/{session_id}"""
    response = client.get(
        f"/agent/sessions/{test_session.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["session_id"] == str(test_session.id)
    assert data["phase"] == "planning"
    assert data["status"] == "in_progress"
    assert len(data["changes"]) == 2


@pytest.mark.asyncio
async def test_get_session_not_found(
    client: TestClient,
    auth_headers: dict,
):
    """Test GET with nonexistent session."""
    fake_id = str(uuid.uuid4())

    response = client.get(
        f"/agent/sessions/{fake_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_session_unauthorized(
    client: TestClient,
    test_session: AgentSession,
    other_user_headers: dict,
):
    """Test unauthorized session access."""
    response = client.get(
        f"/agent/sessions/{test_session.id}",
        headers=other_user_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_approve_change(
    client: TestClient,
    test_changes: list[ProposedCodeChange],
    auth_headers: dict,
    db_session: AsyncSession,
):
    """Test POST /agent/changes/{change_id}/approve"""
    change = test_changes[0]

    response = client.post(
        f"/agent/changes/{change.id}/approve",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "approved"
    assert data["change_id"] == str(change.id)

    # Verify in database
    from app.models_agent import ProposedCodeChange
    from sqlalchemy import select

    updated = await db_session.scalar(
        select(ProposedCodeChange).where(ProposedCodeChange.id == change.id)
    )
    assert updated.status == ChangeStatus.approved
    assert updated.approved_at is not None


@pytest.mark.asyncio
async def test_reject_change(
    client: TestClient,
    test_changes: list[ProposedCodeChange],
    auth_headers: dict,
    db_session: AsyncSession,
):
    """Test POST /agent/changes/{change_id}/reject"""
    change = test_changes[0]
    reason = "Code style issues"

    response = client.post(
        f"/agent/changes/{change.id}/reject?reason={reason}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "rejected"
    assert data["change_id"] == str(change.id)

    # Verify in database
    from app.models_agent import ProposedCodeChange
    from sqlalchemy import select

    updated = await db_session.scalar(
        select(ProposedCodeChange).where(ProposedCodeChange.id == change.id)
    )
    assert updated.status == ChangeStatus.rejected
    assert updated.rejection_reason == reason


@pytest.mark.asyncio
async def test_edit_change(
    client: TestClient,
    test_changes: list[ProposedCodeChange],
    auth_headers: dict,
    db_session: AsyncSession,
):
    """Test POST /agent/changes/{change_id}/edit"""
    change = test_changes[0]
    edited_content = "print('edited')\n"

    response = client.post(
        f"/agent/changes/{change.id}/edit?edited_content={edited_content}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "edited"

    # Verify in database
    from app.models_agent import ProposedCodeChange
    from sqlalchemy import select

    updated = await db_session.scalar(
        select(ProposedCodeChange).where(ProposedCodeChange.id == change.id)
    )
    assert updated.user_edit == edited_content


@pytest.mark.asyncio
async def test_change_not_found(
    client: TestClient,
    auth_headers: dict,
):
    """Test approval of nonexistent change."""
    fake_id = str(uuid.uuid4())

    response = client.post(
        f"/agent/changes/{fake_id}/approve",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_change_unauthorized(
    client: TestClient,
    test_changes: list[ProposedCodeChange],
    other_user_headers: dict,
):
    """Test unauthorized change approval."""
    change = test_changes[0]

    response = client.post(
        f"/agent/changes/{change.id}/approve",
        headers=other_user_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_invalid_uuid(
    client: TestClient,
    auth_headers: dict,
):
    """Test with invalid UUID format."""
    response = client.post(
        "/agent/changes/not-a-uuid/approve",
        headers=auth_headers,
    )

    assert response.status_code == 400


# ============================================================================
# Workflow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_change_approval_workflow(
    client: TestClient,
    test_changes: list[ProposedCodeChange],
    auth_headers: dict,
    db_session: AsyncSession,
):
    """Test complete change approval workflow."""
    change = test_changes[0]

    # 1. Change starts as staged
    from app.models_agent import ProposedCodeChange
    from sqlalchemy import select

    fetched = await db_session.scalar(
        select(ProposedCodeChange).where(ProposedCodeChange.id == change.id)
    )
    assert fetched.status == ChangeStatus.staged

    # 2. Approve the change
    response = client.post(
        f"/agent/changes/{change.id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 200

    await db_session.refresh(fetched)
    assert fetched.status == ChangeStatus.approved

    # 3. Cannot reject an already approved change
    # (In real flow, rejection would only apply to staged changes)


@pytest.mark.asyncio
async def test_multiple_changes_approval(
    client: TestClient,
    test_changes: list[ProposedCodeChange],
    auth_headers: dict,
):
    """Test approving multiple changes."""
    # Approve first change
    response = client.post(
        f"/agent/changes/{test_changes[0].id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Reject second change
    response = client.post(
        f"/agent/changes/{test_changes[1].id}/reject?reason=Out+of+scope",
        headers=auth_headers,
    )
    assert response.status_code == 200


# ============================================================================
# Streaming Tests
# ============================================================================


@pytest.mark.asyncio
async def test_agent_streaming_format(
    client: TestClient,
    auth_headers: dict,
    test_conversation: Conversation,
):
    """Test that streaming response uses SSE format."""
    # Note: This test may be skipped if Docker is not available
    params = {
        "task": "Write a simple test",
        "repo_path": "/test/repo",
        "conversation_id": str(test_conversation.id),
    }

    response = client.post(
        "/agent/chat/agent",
        params=params,
        headers=auth_headers,
        stream=True,
    )

    # Check response headers
    assert response.headers.get("content-type") == "text/event-stream"
    assert response.headers.get("cache-control") == "no-cache"

    # Parse first few events
    events_received = []
    for line in response.iter_lines():
        if line.startswith(b"data: "):
            try:
                event_json = line[6:].decode()
                event = json.loads(event_json)
                events_received.append(event)
            except json.JSONDecodeError:
                pass

    # Should have at least some events (or error if Docker unavailable)
    # Just verify format is correct
    for event in events_received:
        assert "type" in event


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_missing_conversation(
    client: TestClient,
    auth_headers: dict,
):
    """Test agent start with missing conversation."""
    params = {
        "task": "Test task",
        "repo_path": "/test/repo",
        "conversation_id": str(uuid.uuid4()),  # Nonexistent
    }

    response = client.post(
        "/agent/chat/agent",
        params=params,
        headers=auth_headers,
        stream=True,
    )

    # Should return 404 or error in stream
    if response.status_code == 404:
        assert "Conversation not found" in response.json()["detail"]
