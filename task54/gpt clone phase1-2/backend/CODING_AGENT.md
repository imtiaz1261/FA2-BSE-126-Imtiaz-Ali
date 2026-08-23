# Coding Agent Module

Complete production-ready implementation of a ReAct-orchestrated Coding Agent with Docker sandbox isolation, streaming reasoning, and diff-based code review.

## Architecture Overview

### ReAct Loop (Reasoning + Acting)

The agent implements a iterative ReAct pattern:

```
1. PLANNING: LLM creates initial task plan
2. READING: Agent reads relevant files using file_read tool
3. PROPOSING: Agent proposes changes via file_write (staged)
4. AWAITING_APPROVAL: Stream changes to frontend, wait for user approval
5. EXECUTING: Apply approved changes to repository
6. TESTING: Run tests to validate changes
7. SELF_CORRECTING: If tests fail, feed errors back for up to N iterations
8. COMPLETE/FAILED: Terminal state
```

### Streaming Architecture

- **SSE-based**: Server-Sent Events for real-time reasoning visibility
- **Token streaming**: Each event is immediately sent to frontend
- **Non-blocking**: Frontend can interact while agent reasons
- **Recoverable**: All events logged in database for replay

### Docker Sandbox

Each agent session gets an isolated, ephemeral container:

- **Read-only mounts**: Repository mounted as `/workspace:ro`
- **Writable tmpfs**: `/tmp` and `/home` writable for temporary data
- **Resource limits**: CPU, memory, and wall-clock timeouts
- **Network isolation**: No outbound network access
- **Auto-cleanup**: Container destroyed after session ends

### File Staging

Changes are never directly applied:

1. Agent uses `file_write` tool → changes staged in-memory
2. Staging includes auto-generated unified diffs
3. Changes sent to frontend for review
4. User approves/rejects/edits each change
5. Approved changes applied to real repository
6. Each change tracked in database with approval metadata

## Components

### Backend

#### Models (`models_agent.py`)

- **AgentSession**: Tracks session, phase, iterations, errors
- **ProposedCodeChange**: File changes with diffs and approval workflow
- **AgentReasoningStep**: Streaming reasoning steps (thoughts, tool calls, observations)
- **AgentTestExecution**: Test results with pass/fail metrics

#### Services

**Docker Sandbox** (`services/docker_sandbox.py`)
- `SandboxConfig`: Resource limit configuration
- `SandboxContainer`: Individual container management
- `SandboxManager`: Multi-container lifecycle
- `ExecutionResult`: Structured execution output

**Agent Tools** (`services/agent_tools.py`)
- `file_read()`: Read files from repo (path-scoped)
- `file_write()`: Stage changes with diff generation
- `list_files()`: Directory listing
- `shell_exec()`: Execute commands in sandbox
- `run_tests()`: Run test suite
- `git_diff()`: Show staged changes as unified diff

**ReAct Agent** (`services/react_agent.py`)
- `ReactAgent.run()`: Main loop (async generator)
- LLM integration hooks for planning, file reading, change proposal, failure analysis
- Self-correction with configurable iterations
- Database persistence of all states

**Streaming** (`services/agent_streaming.py`)
- `SSEFormatter`: Convert events to SSE format
- `AgentEventStream`: Multi-client event streaming
- `AgentEvents`: Standard event builders (phase_change, reasoning, test_result, etc.)

#### API Routes (`routers/agent.py`)

- `POST /agent/chat/agent`: Start session with streaming
- `POST /agent/changes/{id}/approve`: Approve a change
- `POST /agent/changes/{id}/reject`: Reject with optional reason
- `POST /agent/changes/{id}/edit`: Edit and re-submit change
- `GET /agent/sessions/{id}`: Get session status and history

### Frontend

#### Components

**AgentPanel** (`components/agent/AgentPanel.tsx`)
- Main split-view container
- Left: input form + reasoning log
- Right: diff reviewer
- Handles streaming, approval workflow

**AgentReasoningPanel** (`components/agent/AgentReasoningPanel.tsx`)
- Displays phase indicator with live status
- Renders thought/observation/tool call/result events
- Shows test output and error recovery
- Auto-scrolls to latest events

**DiffReviewPanel** (`components/agent/DiffReviewPanel.tsx`)
- Change list with file icon indicators
- Unified diff viewer with color-coded lines
- Approve/Reject/Edit controls
- Per-change status badges

## Security Model

### Path Traversal Protection

```python
# In AgentTools and file operations
full_path = (repo_path / file_path).resolve()
if not str(full_path).startswith(str(repo_path)):
    raise Exception("Path traversal not allowed")
```

### Docker Isolation

```python
# Read-only filesystem + tmpfs for temp data
docker run \
  --read-only \
  --tmpfs /tmp:size=100m \
  --tmpfs /home:size=100m \
  --memory=512m \
  --cpus=1.0 \
  -v /repo:/workspace:ro \
  --network=none
```

### Approval Workflow

1. No changes auto-apply
2. Every change requires explicit user approval
3. User can edit proposed content before approval
4. Rejection creates audit trail
5. All changes stored with metadata (approver, timestamp, rationale)

## Resource Limits

Configurable per sandbox:

```python
SandboxConfig(
    memory_limit_mb=512,      # Max RAM
    cpu_limit=1.0,            # Max CPU cores
    timeout_seconds=300,      # Max wall-clock time
    network_disabled=True,    # No outbound access
)
```

## Integration with Existing Modules

### Conversation Integration

Agent sessions are tied to conversations:

```python
AgentSession(
    conversation_id=conv.id,  # Link to active conversation
    user_id=user.id,          # Track user ownership
    ...
)
```

### LLM Integration

The `ReactAgent` accepts an `llm_provider` for pluggable LLM:

```python
agent = ReactAgent(
    session=session,
    tools=tools,
    sandbox=sandbox,
    llm_provider=your_llm_client,  # GPT-4, Claude, etc.
)

# Implement these methods to integrate your LLM:
async def _get_plan(self, task: str) -> str
async def _propose_changes(self, task: str, plan: str) -> list[dict]
async def _analyze_failure(self, test_output: str, task: str) -> str
```

### Vision Module Integration

Reasoning can incorporate vision results:

```python
# In agent reasoning, can reference extracted text from Vision module
context = f"""
Task: {task}
Vision analysis: {vision_result.extracted_text}
"""
```

## Database Schema

Migration: `alembic/versions/0003_agent_tables.py`

- `agent_sessions`: Main session tracking
- `proposed_code_changes`: File changes with approval workflow
- `agent_reasoning_steps`: Streaming reasoning steps (for replay/audit)
- `agent_test_executions`: Test results with metrics

Indexes on:
- `(user_id, status)`: For session listing
- `(session_id)`: For change queries
- `(session_id, iteration)`: For reasoning replay

## Testing

### Unit Tests

Run sandbox and tool tests:

```bash
pytest backend/tests/test_agent_sandbox.py -v
```

Tests cover:
- Container lifecycle
- Resource limits
- Path security
- Tool execution
- Error recovery
- Timeouts

### Integration Tests

Run API and workflow tests:

```bash
pytest backend/tests/test_agent_endpoints.py -v
```

Tests cover:
- Session creation
- Change approval workflow
- Streaming response format
- Authorization
- Error handling

### Manual Testing

Start agent session:

```bash
curl -X POST "http://localhost:8000/agent/chat/agent?task=Add+error+handling&repo_path=/path/to/repo&conversation_id=<uuid>" \
  -H "Authorization: Bearer <token>" \
  -H "Accept: text/event-stream"
```

Approve a change:

```bash
curl -X POST "http://localhost:8000/agent/changes/<change_id>/approve" \
  -H "Authorization: Bearer <token>"
```

## Deployment

### Prerequisites

- Docker daemon running (for sandbox)
- PostgreSQL (for agent session tracking)
- Python 3.11+
- Node.js 18+ (frontend)

### Environment Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Frontend
cd frontend
npm install
npm run build
```

### Running Locally

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Frontend dev server
cd frontend
npm run dev
```

### Production Deployment

- Use managed Docker (ECS, GKE, K8s)
- Set resource limits: `SandboxConfig(memory_limit_mb=1024, timeout_seconds=600)`
- Enable logging: Stream events to CloudWatch/Stackdriver
- Rate limit: `/agent/chat/agent` endpoint (1 request per user per minute)
- Cleanup: Cron job to destroy orphaned containers

## Performance Tuning

### Agent Iterations

Default 3 self-corrections; adjust based on task complexity:

```python
session.max_self_corrections = 5  # For complex refactoring tasks
```

### Docker Image

Use smaller base image for faster startup:

```python
SandboxConfig(image="python:3.11-alpine")  # ~40MB vs ~900MB slim
```

### Streaming Optimization

- Batch events in high-throughput scenarios
- Implement server-side event deduplication
- Add event sampling for long reasoning traces

## Troubleshooting

### Docker Connection Issues

```python
# Verify Docker is accessible
docker ps

# Check Docker socket permissions
ls -la /var/run/docker.sock
```

### Sandbox Permission Denied

```bash
# Container tried to write to read-only filesystem
# Temporary files should use /tmp or /home instead
```

### Timeout on Complex Tasks

Increase timeout:

```python
config = SandboxConfig(timeout_seconds=600)  # 10 minutes
```

### Tests Failing in Sandbox

Ensure test framework is installed in container:

```bash
docker run -it python:3.11-slim pip install pytest
```

## Future Enhancements

1. **Multi-file refactoring**: Detect file dependencies for atomic changes
2. **Git integration**: Use git stash for rollback, branches for isolation
3. **LLM caching**: Cache reasoning steps for similar tasks
4. **Custom tools**: Plugin architecture for domain-specific tools
5. **Diff visualization**: Tree-based diff viewer for large changesets
6. **Rollback**: Undo approved changes with one-click revert
7. **Collaboration**: Multi-user approval for enterprise deployments

## Examples

### Task 1: Add Error Handling

```
Task: "Add proper error handling to the auth endpoints"

Agent Flow:
1. Plans: Read auth.py, identify endpoints, propose try/except blocks
2. Reads: auth.py (500 lines), error handler utils
3. Proposes: 3 changes to auth.py with detailed error messages
4. Awaits: User reviews diffs, approves 2, edits 1
5. Executes: Applies 3 approved changes
6. Tests: Runs pytest, finds 1 failing test
7. Corrects: Catches additional exception type, re-runs tests
8. Complete: All tests pass, changes applied
```

### Task 2: Refactor Database Queries

```
Task: "Replace raw SQL with ORM for better maintainability"

Agent Flow:
1. Plans: Audit all SQL queries, identify patterns
2. Reads: db.py, models.py, multiple controller files
3. Proposes: Changes to 5 files with ORM equivalents
4. Awaits: User rejects 1 change (custom SQL needed), approves others
5. Executes: Applies 4 approved changes
6. Tests: Runs integration tests
7. Complete: All tests pass, 1 query remains unchanged
```

## Code Examples

### Starting an Agent Session

```python
from app.services.react_agent import ReactAgent
from app.services.agent_tools import AgentTools
from app.services.docker_sandbox import SandboxManager

# Setup
manager = SandboxManager()
sandbox = await manager.create_container(
    session_id="user-123-task-456",
    repo_path="/path/to/repo",
    config=SandboxConfig(),
)

tools = AgentTools("/path/to/repo", sandbox)
agent = ReactAgent(session, tools, sandbox, llm_provider)

# Run
async for event in agent.run("Add tests for user service", db):
    print(f"Agent: {event['type']} - {event}")

# Cleanup
await manager.destroy_container(session_id)
```

### Approving a Change

```python
# Frontend
const response = await fetch(
  `/api/agent/changes/${changeId}/approve`,
  { method: "POST", headers: { Authorization: `Bearer ${token}` } }
);

// Backend
@router.post("/changes/{change_id}/approve")
async def approve_change(change_id: str, db: AsyncSession):
    change = await db.get(ProposedCodeChange, change_id)
    change.status = ChangeStatus.approved
    await db.commit()
```

## References

- ReAct Paper: https://arxiv.org/abs/2210.03629
- Docker API: https://docs.docker.com/engine/api/
- FastAPI Streaming: https://fastapi.tiangolo.com/advanced/streaming-responses/
- Server-Sent Events: https://html.spec.whatwg.org/multipage/server-sent-events.html
