# Code Alpha VS Code Extension - Implementation Guide

## 📋 Overview

This guide walks through the complete implementation of a professional VS Code extension for the Code Alpha autonomous coding agent, mirroring Kiro's developer experience.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VS Code IDE                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Extension Host (TypeScript)                          │  │
│  │  ┌───────────────────────────────────────────────┐   │  │
│  │  │ WebSocket Client (client.ts)                │   │  │
│  │  │ - Auto-reconnect with backoff              │   │  │
│  │  │ - Message queue for offline buffering      │   │  │
│  │  │ - Event handler dispatch                   │   │  │
│  │  └───────────────────────────────────────────────┘   │  │
│  │                       ↕                                │  │
│  │  ┌───────────────────────────────────────────────┐   │  │
│  │  │ State Manager (stateManager.ts)               │   │  │
│  │  │ - Persistent workspace storage               │   │  │
│  │  │ - Task history & status                      │   │  │
│  │  │ - Spec document versioning                   │   │  │
│  │  │ - Export/Import capabilities                 │   │  │
│  │  └───────────────────────────────────────────────┘   │  │
│  │           ↓              ↓              ↓              │  │
│  │  ┌─────────┴──┬─────────┴──┬─────────┴─────┐         │  │
│  │  ↓           ↓             ↓                 ↓         │  │
│  │  Panel       Inline        Activity         Editor    │  │
│  │  Providers   Decorator     Log              API       │  │
│  │                                                       │  │
│  │  • TaskPanel     • Decorations    • Tree view       │  │
│  │  • SpecsPanel    • Color ranges   • Expand logs     │  │
│  │  • DiffPanel     • Inline hints   • Copy to        │  │
│  │  • WebViews      • Real-time      │ clipboard       │  │
│  │                    updates                          │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Webview Panels (HTML/CSS/JS)                   │  │
│  │  • Monaco Editor integration (optional)         │  │
│  │  • Markdown preview (specs)                    │  │
│  │  • Diff viewer (dual pane)                    │  │
│  │  • Real-time updates via postMessage            │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ↕ WebSocket (JSON Protocol)
┌─────────────────────────────────────────────────────────────┐
│               Code Alpha Backend (Python)                   │
│  • Orchestrator (task scheduling, state machine)          │
│  • Agents (Planner, Coder, Tester, Fixer, Reviewer)      │
│  • Code generation engine (edits, conflict resolution)    │
│  • Test runner (pytest integration)                       │
│  • Healing loop (self-correction)                         │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Project Structure

```
extension/
├── src/
│   ├── extension.ts                      # Main entry point
│   ├── websocket/
│   │   └── client.ts                    # WebSocket connection management
│   ├── state/
│   │   └── stateManager.ts              # Persistent state & storage
│   ├── panels/
│   │   ├── taskPanel.ts                 # Task list webview
│   │   ├── specsPanel.ts                # Requirements/Design/Tasks editor
│   │   ├── diffPanel.ts                 # Change reviewer
│   │   └── activityLog.ts               # Tree view of activities
│   ├── editor/
│   │   └── inlineDecorator.ts           # Real-time edit indicators
│   └── webview/
│       ├── taskPanelContent.ts          # HTML/CSS/JS for tasks
│       ├── specsPanelContent.ts         # HTML/CSS/JS for specs
│       └── diffPanelContent.ts          # HTML/CSS/JS for diffs
├── media/
│   ├── styles.css                       # Shared styling
│   └── icons/
│       └── agent.svg                    # Activity bar icon
├── package.json                         # Extension manifest
├── tsconfig.json                        # TypeScript config
├── README.md                            # User documentation
├── WEBSOCKET_SCHEMA.md                  # Protocol specification
├── backend_example.py                   # Reference backend server
└── .gitignore
```

## 🚀 Implementation Steps

### Step 1: Setup Development Environment

```bash
# Install Node.js and npm
# https://nodejs.org/

# Create extension directory
mkdir extension
cd extension

# Generate extension template (optional)
npm init -y

# Install dependencies
npm install --save-dev @types/vscode @types/node typescript
npm install ws  # WebSocket library
```

### Step 2: Configure TypeScript

Create `tsconfig.json`:
- Target ES2020
- Module: commonjs
- Strict mode enabled
- Output to `./out`

### Step 3: Implement WebSocket Client

**File: `src/websocket/client.ts`**

```typescript
export class AgentWebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: WebSocketEventHandlers;
  private reconnectAttempts = 0;
  private messageQueue: WebSocketMessage[] = [];

  async connect(): Promise<void> {
    // Establish WebSocket connection
    // Implement auto-reconnect with exponential backoff
    // Flush queued messages on connect
  }

  async send(message: WebSocketMessage): Promise<void> {
    // Send message or queue if disconnected
  }

  private handleMessage(data: string) {
    // Dispatch to appropriate handler based on message type
  }
}
```

**Key features:**
- Auto-reconnect with exponential backoff (2s, 4s, 8s, 16s)
- Message queuing while disconnected
- Event handler dispatch
- Connection status tracking

### Step 4: Implement State Manager

**File: `src/state/stateManager.ts`**

```typescript
export class StateManager {
  private tasks: Map<string, Task> = new Map();
  private status: AgentStatus | null = null;
  private specs: Map<string, SpecDocument> = new Map();

  updateTask(task: Task) {
    this.tasks.set(task.id, task);
    this.saveToStorage();
  }

  updateSpec(type, content: string) {
    // Version tracking, modification timestamps
  }

  exportState(): string {
    // For persistence to disk
  }
}
```

**Key features:**
- Persists to VS Code global state
- Versioning for specs
- Export/import for backups
- Task history tracking

### Step 5: Create Panel Providers

Each panel extends VS Code's webview panel pattern:

**TaskPanel (`src/panels/taskPanel.ts`):**
- Shows active tasks with progress
- Real-time status updates
- Pause/Resume/Stop controls
- Click to view logs in output channel

**SpecsPanel (`src/panels/specsPanel.ts`):**
- Three tabs: Requirements, Design, Tasks
- Live markdown preview
- Export/Import functionality
- Version history viewing
- Regenerate cascade support

**DiffPanel (`src/panels/diffPanel.ts`):**
- Side-by-side diff view
- Approve/Reject/Request-Changes actions
- Open file link
- Copy content to clipboard

**ActivityLog (`src/panels/activityLog.ts`):**
- Tree data provider for task history
- Expandable logs per task
- Copy log entries
- Task status icons

### Step 6: Implement Inline Decorations

**File: `src/editor/inlineDecorator.ts`**

```typescript
export class InlineEditDecorator {
  markEditStart(filePath, startLine, endLine) {
    // Yellow border + animation
  }

  markEditComplete(filePath) {
    // Green border, auto-fade after 3s
  }

  markEditError(filePath, startLine, endLine, error) {
    // Red border with error tooltip
  }
}
```

**Features:**
- Color-coded borders (editing/completed/error)
- Gutter icons
- Auto-scroll to show edits
- Hover tooltips
- Auto-fade on completion

### Step 7: Generate Webview Content

Each webview is rendered with HTML/CSS/JS:

```typescript
export function getWebviewContent(webview, extensionUri, data) {
  // Return HTML string with:
  // - nonce for CSP
  // - VS Code theme colors
  // - Real-time update handlers
  // - postMessage communication
}
```

### Step 8: Register Commands

In `extension.ts`:

```typescript
context.subscriptions.push(
  vscode.commands.registerCommand('codeAlphaAgent.pause', async () => {
    await wsClient.send({ type: 'control', action: 'pause' });
  }),
  // ... more commands
);
```

### Step 9: Connect WebSocket Events

In `extension.ts`:

```typescript
wsClient = new AgentWebSocketClient(serverUrl, {
  onTaskUpdate: handleTaskUpdate,      // Update state, refresh panels
  onStatusChange: handleStatusChange,  // Update context flags
  onEditStart: handleEditStart,        // Mark inline decoration
  onDiffReady: handleDiffReady,         // Show diff panel
  onError: handleError,                // Show error notification
});
```

### Step 10: Compile and Package

```bash
# Compile TypeScript
npm run compile

# Test in VS Code
code --extensionDevelopmentPath=. --new-window

# Package as VSIX
npm install -g vsce
vsce package

# Publish (requires account)
vsce publish
```

## 🔌 WebSocket Integration Points

### Client Sends:

```json
// Pause task
{ "type": "control", "action": "pause" }

// Approve changes
{ "type": "review", "action": "approve", "payload": { "diffId": "..." } }

// Update spec
{ "type": "specs", "action": "update", "payload": { "type": "requirements", "content": "..." } }
```

### Client Receives:

```json
// Task started
{ "type": "task_update", "payload": { "id": "...", "state": "Generating", "progress": 0 } }

// Edit complete
{ "type": "edit_end", "payload": { "filePath": "...", "success": true } }

// Diff ready for review
{ "type": "diff_ready", "payload": { "filePath": "...", "oldContent": "...", "newContent": "..." } }
```

## 🎨 UI/UX Patterns

### Task Panel

```
┌─────────────────────────────────────┐
│  🤖 Code Alpha Agent    Status: ⚙️  │
├─────────────────────────────────────┤
│  [⏸ Pause] [▶ Resume] [⏹ Stop]     │
├─────────────────────────────────────┤
│  ✓ Task 1: Generate Auth Module     │
│    Progress: ████████░░░ 70%        │
│    State: Testing                   │
│    📋 View 5 log entries            │
│                                     │
│  ⚙️ Task 2: Generate API Endpoints  │
│    Progress: ██░░░░░░░░░ 20%        │
│    State: Generating                │
├─────────────────────────────────────┤
│  No more tasks                      │
└─────────────────────────────────────┘
```

### Inline Edit Decoration

```python
# File is being edited by agent
def authenticate(username, password):  ← Yellow border
    # Computing...                      ← Edit in progress
    pass
```

After completion:
```python
def authenticate(username, password):  ← Green border for 3s
    if username not in users:
        return False
    return users[username] == hash(password)
```

### Diff Panel

```
┌────────────────────────────────────┐
│  👁️ Review Changes                  │
│  src/auth.py (lines 1-32)           │
├────────────────────────────────────┤
│ Before              │   After       │
│ (empty)             │ def __init__  │
│                     │   self.users  │
│                     │   = {}        │
├────────────────────────────────────┤
│ [✅ Approve] [💬 Request] [❌ Reject]
└────────────────────────────────────┘
```

### Specs Panel

```
┌────────────────────────────────────┐
│  📋 Specifications                  │
│ [Requirements] [Design] [Tasks]     │
├────────────────────────────────────┤
│ # Project Requirements              │
│ - Authentication system             │
│ - User management                   │
│ - API endpoints                     │
│                                     │
│ Version 2 • Modified 2 hours ago    │
│ [Save] [Regenerate From Here]      │
└────────────────────────────────────┘
```

## 🧪 Testing

### Unit Tests
```bash
# Install testing framework
npm install --save-dev @vscode/test-electron mocha @types/mocha

# Run tests
npm test
```

### Manual Testing
1. Open extension in development mode
2. Open Code Alpha project in workspace
3. Trigger each command manually
4. Verify state persistence
5. Test WebSocket reconnection (kill server, restart)

### Integration Testing
1. Start backend server: `python extension/backend_example.py`
2. Launch extension
3. Observe live task updates
4. Test approve/reject flow
5. Verify inline decorations

## 📊 Monitoring & Debugging

### Enable Debug Output

In extension:
```typescript
const DEBUG = true;

function log(...args: any[]) {
  if (DEBUG) console.log('[Code Alpha]', ...args);
}
```

View in: `View → Output → Code Alpha Agent`

### WebSocket Debugging

Use `wscat`:
```bash
npm install -g wscat
wscat -c ws://localhost:8765
```

Monitor live messages:
```
> {"type":"control","action":"pause"}
< {"type":"status_change","payload":{"state":"AwaitingReview"}}
```

### State Inspection

Export state from dev tools:
```typescript
const state = context.globalState.get('codeAlphaAgent.state');
console.log(JSON.stringify(state, null, 2));
```

## 🔐 Security Considerations

1. **CSP (Content Security Policy)**
   - Use nonce for inline scripts
   - Restrict script sources
   - Validate all external content

2. **WebSocket Validation**
   - Validate message structure
   - Type-check payloads
   - Rate-limit client requests

3. **State Storage**
   - No secrets in global state
   - Use VS Code secrets API for credentials
   - Encrypt sensitive data

4. **File Operations**
   - Validate file paths
   - Check workspace permissions
   - Use `Uri` class for safe paths

## 📈 Performance Optimization

1. **Webview Rendering**
   ```typescript
   retainContextWhenHidden: true  // Keep state between views
   enableScripts: true            // Only for interactive panels
   ```

2. **Update Frequency**
   - Batch WebSocket updates
   - Debounce decorations
   - Throttle tree view refresh

3. **Memory Management**
   ```typescript
   this.disposables.forEach(d => d.dispose());
   ```

## 🚀 Deployment

### Marketplace Publishing

1. Create publisher account on [VS Code Marketplace](https://marketplace.visualstudio.com)
2. Generate Personal Access Token (PAT)
3. Install vsce: `npm install -g vsce`
4. Package: `vsce package`
5. Publish: `vsce publish`

### Configuration in package.json

```json
{
  "publisher": "codealpha",
  "name": "code-alpha-agent",
  "displayName": "Code Alpha Agent",
  "version": "0.1.0"
}
```

## 📚 References

- [VS Code Extension API](https://code.visualstudio.com/api)
- [WebSocket Protocol (RFC 6455)](https://tools.ietf.org/html/rfc6455)
- [TypeScript Documentation](https://www.typescriptlang.org/)
- [Code Alpha Backend](../README.md)

## 🎯 Next Steps

1. ✅ Complete extension implementation
2. ✅ Integrate with Code Alpha backend
3. ✅ Add comprehensive testing
4. ✅ Create user documentation
5. ✅ Submit to VS Code Marketplace
6. ⏳ Gather community feedback
7. ⏳ Add advanced features:
   - Code diffing with diff-match-patch
   - Monaco Editor integration
   - Custom theme support
   - Collaborative features
   - Cloud backup/sync

---

**Status**: Implementation complete with all core components ready for integration with Code Alpha backend.

**Last Updated**: August 2026
