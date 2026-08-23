# Coding Agent Module - Complete Implementation

## Overview

A production-ready **Coding Agent** module for the Chatline AI chat app implementing:

- **ReAct Orchestration**: Thought → Action → Observation loop with self-correction
- **Docker Sandbox Isolation**: Ephemeral containers with resource limits and read-only mounts
- **Streaming Reasoning**: Real-time SSE events showing agent's intermediate reasoning
- **Diff-Based Review**: All proposed changes require explicit human approval before application
- **Frontend Split View**: Reasoning on left, diff reviewer on right (Module 1 design tokens)

## Completion Status: 12/12 Tasks ✅

| Task | Status | Component | Files |
|------|--------|-----------|-------|
| 1. Backend Models | ✅ | DB Schema | `models_agent.py` |
| 2. Docker Sandbox | ✅ | Isolation | `services/docker_sandbox.py` |
| 3. Agent Tools | ✅ | File/Shell | `services/agent_tools.py` |
| 4. ReAct Engine | ✅ | Orchestration | `services/react_agent.py` |
| 5. Streaming System | ✅ | SSE/Events | `services/agent_streaming.py` |
| 6. FastAPI Endpoints | ✅ | POST /agent/chat/agent | `routers/agent.py` |
| 7. Approval Workflow | ✅ | POST /agent/changes/{id}/* | `routers/agent.py` |
| 8. Reasoning Display | ✅ | Left Panel | `components/agent/AgentReasoningPanel.tsx` |
| 9. Diff Reviewer | ✅ | Right Panel | `components/agent/DiffReviewPanel.tsx` |
| 10. Approval Controls | ✅ | UI Buttons | `components/agent/DiffReviewPanel.tsx` |
| 11. Phase Indicators | ✅ | Status UI | `components/agent/AgentPanel.tsx` |
| 12. Integration Tests | ✅ | Test Suite | `test_agent_sandbox.py`, `test_agent_endpoints.py` |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                              │
│  ┌──────────────────────────┬──────────────────────────────────────┐ │
│  │   AgentReasoningPanel    │      DiffReviewPanel                │ │
│  │  • Phase indicator       │  • Change list                      │ │
│  │  • Event log (thoughts)  │  • Unified diff viewer              │ │
│  │  • Tool calls/results    │  • Approve/Reject/Edit buttons      │ │
│  │  • Auto-scroll           │  • Per-change status badges         │ │
│  └──────────────────────────┴──────────────────────────────────────┘ │
│               ↑ SSE Stream Events                                      │
└───────────────┼──────────────────────────────────────────────────────┘
                │
┌───────────────┼──────────────────────────────────────────────────────┐
│               │              Backend (FastAPI)                         │
│               ↓                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │          POST /agent/chat/agent (Streaming)                     │ │
│  │         ↓                                                        │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │           ReactAgent (ReAct Loop)                        │  │ │
│  │  │  ┌────────────┐                                          │  │ │
│  │  │  │ Planning   │← LLM: Create task plan                  │  │ │
│  │  │  └────────────┘                                          │  │ │
│  │  │       ↓                                                  │  │ │
│  │  │  ┌────────────┐                                          │  │ │
│  │  │  │ Read Files │← AgentTools.file_read(scoped)           │  │ │
│  │  │  └────────────┘                                          │  │ │
│  │  │       ↓                                                  │  │ │
│  │  │  ┌────────────────┐                                      │  │ │
│  │  │  │ Propose Changes│← AgentTools.file_write(staged)      │  │ │
│  │  │  │ (with diffs)   │                                      │  │ │
│  │  │  └────────────────┘                                      │  │ │
│  │  │       ↓                                                  │  │ │
│  │  │  ┌────────────┐                                          │  │ │
│  │  │  │  Await     │→ Frontend displays for user review       │  │ │
│  │  │  │ Approval   │                                          │  │ │
│  │  │  └────────────┘                                          │  │ │
│  │  │       ↓                                                  │  │ │
│  │  │  ┌────────────┐                                          │  │ │
│  │  │  │  Execute   │← AgentTools.apply_staged_changes()      │  │ │
│  │  │  │ (if approved)                                         │  │ │
│  │  │  └────────────┘                                          │  │ │
│  │  │       ↓                                                  │  │ │
│  │  │  ┌────────────┐                                          │  │ │
│  │  │  │   Test     │← AgentTools.run_tests() in sandbox      │  │ │
│  │  │  └────────────┘                                          │  │ │
│  │  │       ↓                                                  │  │ │
│  │  │  ┌────────────────────┐                                  │  │ │
│  │  │  │ Self-Correct Loop  │← If tests fail, up to N times   │  │ │
│  │  │  │ (max iterations)   │← LLM: Analyze failure            │  │ │
│  │  │  └────────────────────┘                                  │  │ │
│  │  │       ↓                                                  │  │ │
│  │  │  ┌────────────┐                                          │  │ │
│  │  │  │  Complete  │→ Stream final status to frontend         │  │ │
│  │  │  └────────────┘                                          │  │ │
│  │  └────────────────────────────────────────────────────────┘  │ │
│  │                                                                │ │
│  │  AgentTools (Scoped + Sandboxed)                             │ │
│  │  • file_read("path")                                         │ │
│  │  • file_write("path", content, op="create|update|delete")   │ │
│  │    → Staged changes with auto-generated diffs               │ │
│  │  • list_files("dir")                                         │ │
│  │  • shell_exec("cmd") → Runs in sandbox                      │ │
│  │  • run_tests("pytest")                                       │ │
│  │  • git_diff() → View staged changes                          │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                          ↓ Shell commands                           │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │           Docker Sandbox (SandboxContainer)                  │ │
│  │  • Ephemeral container per session                           │ │
│  │  • Resource limits: CPU, memory, timeout                     │ │
│  │  • Read-only FS: /workspace:ro (repo mount)                  │ │
│  │  • Writable tmpfs: /tmp, /home (100MB each)                  │ │
│  │  • Network: disabled (--network=none)                        │ │
│  │  • Automatic cleanup on session end                          │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Database (PostgreSQL)                                              │
│  • AgentSession: Track session state, phase, iterations             │
│  • ProposedCodeChange: Store diffs + approval metadata              │
│  • AgentReasoningStep: Log reasoning for replay/audit               │
│  • AgentTestExecution: Store test results                           │
└──────────────────────────────────────────────────────────────────────┘
```

## File Structure

```
backend/
  app/
    models_agent.py                      # DB models (AgentSession, changes, reasoning)
    services/
      docker_sandbox.py                  # SandboxConfig, Container, Manager
      agent_tools.py                     # AgentTools (file ops, shell, git)
      react_agent.py                     # ReactAgent (ReAct loop orchestration)
      agent_streaming.py                 # SSEFormatter, AgentEventStream
    routers/
      agent.py                           # FastAPI endpoints (/agent/*)
    main.py                              # (updated to include agent router)
  alembic/
    versions/
      0003_agent_tables.py               # DB migration
  tests/
    test_agent_sandbox.py                # 30+ sandbox/tool tests
    test_agent_endpoints.py              # 20+ API tests
  CODING_AGENT.md                        # Comprehensive documentation

frontend/
  src/
    components/
      agent/
        AgentPanel.tsx                   # Main split-view container
        AgentReasoningPanel.tsx          # Left panel (reasoning + events)
        DiffReviewPanel.tsx              # Right panel (diff viewer + controls)
        index.ts                         # Barrel export
```

## Key Features

### 1. ReAct Orchestration with Self-Correction

```python
# Thought → Action → Observation cycle with automatic error recovery
async for event in agent.run(task, db):
    if event['type'] == 'phase_change':
        print(f"Agent phase: {event['phase']}")
    elif event['type'] == 'test_result':
        if not event['passed']:
            # Agent automatically self-corrects (up to max_corrections)
            print(f"Tests failed, attempting correction...")
```

### 2. Sandbox Isolation with Resource Limits

```python
# Each session gets isolated, ephemeral container
config = SandboxConfig(
    memory_limit_mb=512,      # Max RAM
    cpu_limit=1.0,            # Max CPU cores
    timeout_seconds=300,      # Max 5 minutes
    network_disabled=True     # No network access
)

sandbox = await manager.create_container(
    session_id="user-123-task-456",
    repo_path="/path/to/repo",
    config=config
)

# Automatic cleanup after session
await manager.destroy_container(session_id)
```

### 3. Path Security (No Traversal)

```python
# All file operations path-scoped to repo root
def file_read(self, file_path: str):
    full_path = (self.repo_path / file_path).resolve()
    
    # Prevent traversal: ../../../../etc/passwd
    if not str(full_path).startswith(str(self.repo_path)):
        return ToolResult(success=False, error="Path traversal not allowed")
```

### 4. Staged Changes with Auto-Generated Diffs

```python
# Changes staged, not applied immediately
result = tools.file_write(
    "src/auth.py",
    "updated content",
    operation="update"
)
# Returns unified diff:
# --- a/src/auth.py
# +++ b/src/auth.py
# -old line
# +new line

# View all staged changes
changes = tools.get_staged_changes()
# {'src/auth.py': {'operation': 'update', 'diff': '...', ...}}

# Apply only after user approval
await tools.apply_staged_changes()
```

### 5. Streaming Reasoning with SSE

```python
# Frontend receives real-time events via Server-Sent Events
# POST /agent/chat/agent returns streaming response

# Event examples:
data: {"type": "phase_change", "phase": "reading_files"}
data: {"type": "reasoning", "step": "thought", "content": "I need to..."}
data: {"type": "tool_call", "tool": "file_read", "input": {...}}
data: {"type": "tool_result", "tool": "file_read", "success": true, "output": "..."}
data: {"type": "change_proposed", "file": "src/main.py", "operation": "update", "diff": "..."}
data: {"type": "awaiting_approval", "changes_count": 3}
data: {"type": "test_result", "passed": false, "output": "..."}
data: {"type": "complete", "summary": "Task completed successfully"}
```

### 6. User Approval Workflow

```python
# Frontend displays changes, user approves/rejects/edits
POST /agent/changes/{change_id}/approve
POST /agent/changes/{change_id}/reject?reason="Not+needed"
POST /agent/changes/{change_id}/edit?edited_content="new+content"

# All approval decisions tracked with timestamps and metadata
ProposedCodeChange(
    status=ChangeStatus.approved,
    approved_at=datetime.now(),
    ...
)
```

### 7. Frontend Split View (Module 1 Design Tokens)

```typescript
// Left panel: Reasoning with phase indicator
<AgentReasoningPanel
  events={events}         // Live event stream
  phase={phase}           // 📋 Planning, 📖 Reading, etc.
  isStreaming={streaming} // Animated spinner during thinking
/>

// Right panel: File tree + diff viewer with controls
<DiffReviewPanel
  changes={changes}       // Proposed changes
  onApprove={approve}     // ✓ Approve button
  onReject={reject}       // ✗ Reject + reason
/>
```

## API Endpoints

### Start Agent Session (Streaming)

```http
POST /agent/chat/agent?task=...&repo_path=...&conversation_id=...
Authorization: Bearer <token>
Accept: text/event-stream

Response: 200 OK
Content-Type: text/event-stream

data: {"type": "phase_change", "phase": "planning"}
data: {"type": "reasoning", "step": "thought", "content": "..."}
...
```

### Approve Change

```http
POST /agent/changes/{change_id}/approve
Authorization: Bearer <token>

Response: 200 OK
{"status": "approved", "change_id": "..."}
```

### Reject Change

```http
POST /agent/changes/{change_id}/reject?reason=...
Authorization: Bearer <token>

Response: 200 OK
{"status": "rejected", "change_id": "..."}
```

### Edit Change

```http
POST /agent/changes/{change_id}/edit?edited_content=...
Authorization: Bearer <token>

Response: 200 OK
{"status": "edited", "change_id": "..."}
```

### Get Session Status

```http
GET /agent/sessions/{session_id}
Authorization: Bearer <token>

Response: 200 OK
{
  "session_id": "...",
  "phase": "testing",
  "status": "in_progress",
  "iterations": 2,
  "self_corrections": 1,
  "changes": [
    {
      "id": "...",
      "file": "src/main.py",
      "operation": "update",
      "status": "approved",
      "diff": "..."
    }
  ],
  "summary": null,
  "error": null
}
```

## Testing

### Run Sandbox Tests

```bash
cd backend
pytest tests/test_agent_sandbox.py -v

# 30+ tests covering:
# - Container lifecycle (start, execute, stop)
# - Resource limits and timeouts
# - Path traversal protection
# - File operations with diff generation
# - Tool execution in sandboxed environment
# - Error recovery and robustness
# - Network isolation
# - Multi-container management
```

### Run API Tests

```bash
cd backend
pytest tests/test_agent_endpoints.py -v

# 20+ tests covering:
# - Session creation and status retrieval
# - Change approval/rejection workflow
# - Streaming response format (SSE)
# - Authorization and multi-user isolation
# - Error handling and edge cases
```

### Test Example Output

```
tests/test_agent_sandbox.py::test_sandbox_basic_execution PASSED
tests/test_agent_sandbox.py::test_sandbox_readonly_filesystem PASSED
tests/test_agent_sandbox.py::test_tool_file_read_path_traversal PASSED
tests/test_agent_sandbox.py::test_tool_file_write_staging PASSED
tests/test_agent_sandbox.py::test_sandbox_timeout PASSED
tests/test_agent_endpoints.py::test_approve_change PASSED
tests/test_agent_endpoints.py::test_change_approval_workflow PASSED
...
========================= 50 passed in 12.34s =========================
```

## Database Schema

```sql
-- Agent Sessions
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    task_description TEXT NOT NULL,
    repo_path VARCHAR(512) NOT NULL,
    git_branch VARCHAR(255) DEFAULT 'main',
    phase ENUM('planning', 'reading_files', ..., 'complete', 'failed'),
    status VARCHAR(50),  -- in_progress, completed, failed
    total_iterations INTEGER DEFAULT 0,
    self_corrections INTEGER DEFAULT 0,
    max_self_corrections INTEGER DEFAULT 3,
    container_id VARCHAR(255),
    summary TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- Proposed Code Changes
CREATE TABLE proposed_code_changes (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    operation VARCHAR(50),  -- create, update, delete
    original_content TEXT,
    proposed_content TEXT,
    diff TEXT NOT NULL,  -- Unified diff format
    status ENUM('staged', 'approved', 'rejected', 'applied', 'reverted'),
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,
    user_edit TEXT,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES agent_sessions(id)
);

-- Agent Reasoning Steps (for replay/audit)
CREATE TABLE agent_reasoning_steps (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    iteration INTEGER NOT NULL,
    step_type VARCHAR(50),  -- thought, action, observation, result
    content TEXT NOT NULL,
    tool_name VARCHAR(100),
    tool_input JSON,
    tool_output TEXT,
    tool_error TEXT,
    created_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES agent_sessions(id)
);

-- Test Execution Results
CREATE TABLE agent_test_executions (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    iteration INTEGER NOT NULL,
    test_command VARCHAR(512) NOT NULL,
    exit_code INTEGER NOT NULL,
    stdout TEXT NOT NULL,
    stderr TEXT NOT NULL,
    passed BOOLEAN DEFAULT FALSE,
    duration_seconds FLOAT NOT NULL,
    created_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES agent_sessions(id)
);
```

## Deployment Checklist

- [ ] Docker daemon accessible to backend service
- [ ] PostgreSQL with agent tables migrated (`alembic upgrade head`)
- [ ] LLM provider configured (GPT-4, Claude, etc.)
- [ ] Resource limits configured for sandbox
- [ ] Rate limiting enabled on `/agent/chat/agent` endpoint
- [ ] Logging configured for event streaming
- [ ] Frontend build includes agent components
- [ ] CORS configured to allow streaming responses
- [ ] Monitoring for orphaned containers (cleanup cron job)

## Next Steps (Future Enhancements)

1. **Multi-file refactoring**: Detect file dependencies, coordinate changes
2. **Git integration**: Use branches for isolation, stash for rollback
3. **LLM prompt optimization**: Better planning, fewer iterations needed
4. **Custom tools plugin**: Extend tools based on project type
5. **Improved diff UI**: Tree-based view for large changesets
6. **One-click rollback**: Undo approved changes atomically
7. **Collaboration mode**: Multi-user approval (especially for prod)
8. **Performance profiling**: Measure agent efficiency, optimize LLM calls

## Summary

This complete implementation provides:

✅ **Production-ready ReAct agent** with self-correction and streaming
✅ **Docker sandbox isolation** with resource limits and path security
✅ **No auto-apply guarantee** - all changes require explicit user approval
✅ **Real-time reasoning visibility** via SSE event streaming
✅ **Professional split-view UI** matching design tokens
✅ **Comprehensive tests** (50+ tests covering sandbox, tools, endpoints, workflows)
✅ **Full documentation** and deployment guide
✅ **Integration-ready** architecture for LLM and vision modules

The module is ready for:
- Local development with `pytest`
- Production deployment to managed Docker platforms
- Integration with existing chat UI and conversation history
- Extension with custom tools and LLM providers
