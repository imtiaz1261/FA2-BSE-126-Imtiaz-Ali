# WebSocket Communication Schema

This document defines the complete WebSocket message protocol between the Code Alpha VS Code Extension and the Backend Orchestrator.

## Overview

- **Transport**: WebSocket (RFC 6455)
- **Data Format**: JSON
- **Default Server**: `ws://localhost:8765`
- **Connection Lifecycle**: Persistent with automatic reconnection (exponential backoff)

---

## Message Structure

All messages follow this base structure:

```json
{
  "type": "string",
  "payload": {},
  "metadata": {
    "timestamp": "number",
    "requestId": "string"
  }
}
```

---

## Client → Server Messages (Extension Sends)

### 1. Control Messages

Control the orchestrator's task execution flow.

#### Pause Task
```json
{
  "type": "control",
  "action": "pause",
  "payload": {
    "taskId": "string (optional)"
  }
}
```

**Response**: 
```json
{
  "type": "status_change",
  "payload": {
    "state": "AwaitingReview",
    "message": "Task paused by user"
  }
}
```

#### Resume Task
```json
{
  "type": "control",
  "action": "resume",
  "payload": {
    "taskId": "string (optional)"
  }
}
```

**Response**:
```json
{
  "type": "status_change",
  "payload": {
    "state": "Generating",
    "message": "Task resumed"
  }
}
```

#### Stop Task
```json
{
  "type": "control",
  "action": "stop",
  "payload": {
    "taskId": "string (optional)",
    "reason": "string (optional)"
  }
}
```

**Response**:
```json
{
  "type": "status_change",
  "payload": {
    "state": "Failed",
    "message": "Task stopped by user"
  }
}
```

---

### 2. Review Messages

Approve or request changes to proposed diffs.

#### Approve Changes
```json
{
  "type": "review",
  "action": "approve",
  "payload": {
    "diffId": "string",
    "comment": "string (optional)"
  }
}
```

**Response**:
```json
{
  "type": "diff_approved",
  "payload": {
    "diffId": "string",
    "message": "Changes approved. Proceeding to next task."
  }
}
```

#### Reject Changes
```json
{
  "type": "review",
  "action": "reject",
  "payload": {
    "diffId": "string",
    "reason": "string"
  }
}
```

**Response**:
```json
{
  "type": "diff_rejected",
  "payload": {
    "diffId": "string",
    "message": "Changes rejected. Reverting changes."
  }
}
```

#### Request Changes
```json
{
  "type": "review",
  "action": "request-changes",
  "payload": {
    "diffId": "string",
    "feedback": "string",
    "severity": "info|warning|error"
  }
}
```

**Response**:
```json
{
  "type": "changes_requested",
  "payload": {
    "diffId": "string",
    "message": "Feedback recorded. Agent will refactor based on your input."
  }
}
```

---

### 3. Spec Messages

Manage specification documents.

#### Update Spec
```json
{
  "type": "specs",
  "action": "update",
  "payload": {
    "type": "requirements|design|tasks",
    "content": "string",
    "version": "number (optional, for conflict detection)"
  }
}
```

**Response**:
```json
{
  "type": "spec_updated",
  "payload": {
    "type": "requirements",
    "version": 2,
    "message": "Requirements updated. Design spec marked stale."
  }
}
```

#### Regenerate Specs
```json
{
  "type": "specs",
  "action": "regenerate",
  "payload": {
    "from": "requirements|design|tasks (optional)",
    "cascade": "boolean (default: true)"
  }
}
```

**Response**:
```json
{
  "type": "spec_generation_started",
  "payload": {
    "taskId": "string",
    "message": "Regenerating specs from requirements..."
  }
}
```

#### Get Spec History
```json
{
  "type": "specs",
  "action": "history",
  "payload": {
    "type": "requirements|design|tasks",
    "limit": "number (default: 10)"
  }
}
```

**Response**:
```json
{
  "type": "spec_history",
  "payload": {
    "type": "requirements",
    "versions": [
      {
        "version": 3,
        "content": "string",
        "timestamp": "number",
        "author": "string"
      }
    ]
  }
}
```

---

## Server → Client Messages (Backend Sends)

### 1. Task Update Messages

Real-time updates about task execution.

#### Task Started
```json
{
  "type": "task_update",
  "payload": {
    "id": "string",
    "name": "string",
    "state": "Planning",
    "progress": 0,
    "startTime": 1234567890,
    "description": "string"
  }
}
```

#### Task Progress
```json
{
  "type": "task_update",
  "payload": {
    "id": "string",
    "name": "string",
    "state": "Generating|Testing|Fixing",
    "progress": 0-100,
    "currentStep": "string (e.g., 'Running tests...')",
    "elapsedTime": "number (ms)"
  }
}
```

#### Task Completed
```json
{
  "type": "task_update",
  "payload": {
    "id": "string",
    "name": "string",
    "state": "Complete",
    "progress": 100,
    "startTime": 1234567890,
    "endTime": 1234567950,
    "summary": "string"
  }
}
```

#### Task Failed
```json
{
  "type": "task_update",
  "payload": {
    "id": "string",
    "name": "string",
    "state": "Failed",
    "progress": 50,
    "error": "string (error message)",
    "errorDetails": {
      "type": "string",
      "file": "string (optional)",
      "line": "number (optional)"
    }
  }
}
```

---

### 2. Status Change Messages

Notify of orchestrator state transitions.

```json
{
  "type": "status_change",
  "payload": {
    "state": "Planning|Generating|Testing|Fixing|AwaitingReview|Complete|Failed|Idle",
    "currentTask": "string (optional)",
    "timestamp": 1234567890,
    "details": "string (optional)",
    "nextAction": "string (optional)"
  }
}
```

---

### 3. Edit Stream Messages

Real-time feedback as agent edits files.

#### Edit Start
```json
{
  "type": "edit_start",
  "payload": {
    "filePath": "string",
    "operation": "create|replace|insert",
    "startLine": "number (for replace/insert)",
    "endLine": "number (for replace)",
    "description": "string (e.g., 'Adding error handling')"
  }
}
```

#### Edit Progress
```json
{
  "type": "edit_progress",
  "payload": {
    "filePath": "string",
    "lineNumber": "number",
    "content": "string (current line being edited)"
  }
}
```

#### Edit End
```json
{
  "type": "edit_end",
  "payload": {
    "filePath": "string",
    "success": "boolean",
    "linesChanged": "number",
    "error": "string (optional)"
  }
}
```

---

### 4. Diff Ready Messages

When changes are ready for review.

```json
{
  "type": "diff_ready",
  "payload": {
    "diffId": "string (unique identifier)",
    "filePath": "string",
    "oldContent": "string",
    "newContent": "string",
    "startLine": "number",
    "endLine": "number",
    "changeType": "modification|creation|deletion",
    "description": "string (e.g., 'Refactored authentication logic')",
    "requiresApproval": "boolean (default: true)"
  }
}
```

---

### 5. Log Messages

Stream task logs in real-time.

```json
{
  "type": "log",
  "payload": {
    "taskId": "string",
    "level": "info|warning|error|debug",
    "message": "string",
    "timestamp": 1234567890,
    "context": {
      "file": "string (optional)",
      "line": "number (optional)"
    }
  }
}
```

---

### 6. Error Messages

Error notifications.

```json
{
  "type": "error",
  "payload": {
    "code": "string (e.g., 'AGENT_CRASHED')",
    "message": "string",
    "severity": "info|warning|error|fatal",
    "recoverable": "boolean",
    "suggestion": "string (optional)"
  }
}
```

---

### 7. Connection Control

#### Connection Established
```json
{
  "type": "connected",
  "payload": {
    "sessionId": "string",
    "version": "string (server version)",
    "features": ["string"]
  }
}
```

#### Heartbeat (Ping)
```json
{
  "type": "ping",
  "payload": {
    "timestamp": 1234567890
  }
}
```

**Client Response** (Pong):
```json
{
  "type": "pong",
  "payload": {
    "timestamp": 1234567890
  }
}
```

#### Connection Closing
```json
{
  "type": "disconnecting",
  "payload": {
    "reason": "string",
    "code": "number"
  }
}
```

---

## Error Handling

### Connection Errors

| Error Code | Description | Recovery |
|-----------|-------------|----------|
| 1000 | Normal closure | Reconnect with backoff |
| 1001 | Going away | Reconnect with backoff |
| 1002 | Protocol error | Log and reconnect |
| 1006 | Abnormal closure | Reconnect with exponential backoff |
| 1011 | Server error | Reconnect with backoff |

### Message Validation Errors

If a message is invalid, the server responds:

```json
{
  "type": "error",
  "payload": {
    "code": "INVALID_MESSAGE",
    "message": "Invalid message format",
    "originalMessage": "...",
    "validationErrors": ["type field missing", "payload is not an object"]
  }
}
```

---

## Reconnection Strategy

The client implements exponential backoff reconnection:

```
Attempt 1: Immediate
Attempt 2: Wait 2s
Attempt 3: Wait 4s
Attempt 4: Wait 8s
Attempt 5: Wait 16s
Max attempts: 5 (then fails)
```

---

## Example Interaction

### Complete Flow

1. **User clicks "Pause"**
   ```json
   → { "type": "control", "action": "pause" }
   ```

2. **Server confirms pause and agent pauses**
   ```json
   ← { "type": "status_change", "payload": { "state": "AwaitingReview" } }
   ```

3. **User reviews diff**
   ```json
   ← { "type": "diff_ready", "payload": { "filePath": "...", "oldContent": "...", "newContent": "..." } }
   ```

4. **User approves**
   ```json
   → { "type": "review", "action": "approve", "payload": { "diffId": "..." } }
   ```

5. **Server confirms and continues**
   ```json
   ← { "type": "diff_approved", "payload": { "diffId": "...", "message": "..." } }
   ← { "type": "status_change", "payload": { "state": "Testing" } }
   ← { "type": "task_update", "payload": { "state": "Testing", "progress": 60 } }
   ```

---

## Implementation Notes

### TypeScript Types

```typescript
interface WebSocketMessage {
  type: string;
  payload?: any;
  metadata?: {
    timestamp: number;
    requestId?: string;
  };
}

interface TaskUpdateMessage extends WebSocketMessage {
  type: 'task_update';
  payload: {
    id: string;
    name: string;
    state: TaskState;
    progress: number;
    startTime: number;
    endTime?: number;
    error?: string;
    logs?: string[];
  };
}

interface DiffReadyMessage extends WebSocketMessage {
  type: 'diff_ready';
  payload: {
    diffId: string;
    filePath: string;
    oldContent: string;
    newContent: string;
    startLine: number;
    endLine: number;
  };
}
```

### Testing

Use `wscat` for manual testing:

```bash
npm install -g wscat

# Connect to server
wscat -c ws://localhost:8765

# Send message
> {"type":"control","action":"pause"}

# Receive response
< {"type":"status_change","payload":{"state":"AwaitingReview"}}
```

---

## Versioning

Current schema version: **1.0**

Breaking changes will increment the major version. The server includes the version in the `connected` message.

```json
{
  "type": "connected",
  "payload": {
    "version": "1.0"
  }
}
```

Clients should validate version compatibility on connection.
