# Code Alpha Agent VS Code Extension

A professional VS Code extension providing a real-time IDE interface for autonomous spec-driven coding agent orchestration. Features live task monitoring, inline edit decorations, diff viewing, and spec management — similar to Kiro's developer experience.

## Features

### 1. **Task Panel** 👁️
- Real-time task status monitoring with live progress bars
- Visual state indicators (Planning → Generating → Testing → Fixing → AwaitingReview)
- Task logs and activity history
- Pause/Resume/Stop controls
- Inline task details with timestamps

### 2. **Inline Edits** ⚡
- Real-time decoration showing which lines are being edited
- Visual feedback with color-coded states:
  - Yellow border: edit in progress
  - Green border: edit completed
  - Red border: edit error
- Auto-reveals edited code in editor
- Gutter icons for quick visual identification

### 3. **Diff Viewer** 📝
- Side-by-side diff visualization
- Before/After comparison
- Line-by-line changes with context
- Review actions:
  - ✅ **Approve**: Accept proposed changes
  - ❌ **Reject**: Decline with optional reason
  - 💬 **Request Changes**: Provide specific feedback

### 4. **Specs Panel** 📋
- **Requirements Tab**: Define project requirements
- **Design Tab**: Document architecture and design decisions
- **Tasks Tab**: Break down implementation tasks
- Version history tracking
- Live markdown preview
- Export/Import specs
- Regenerate from any point in the spec chain

### 5. **Activity Log** 📊
- Tree-view of all tasks and logs
- Expandable task details
- Copy log entries to clipboard
- Quick access to task history

## Architecture

### Core Components

```
extension/
├── src/
│   ├── extension.ts                 # Main extension entry point
│   ├── websocket/
│   │   └── client.ts               # WebSocket client for agent communication
│   ├── state/
│   │   └── stateManager.ts         # Durable state persistence
│   ├── panels/
│   │   ├── taskPanel.ts            # Task list webview provider
│   │   ├── specsPanel.ts           # Specs editor webview provider
│   │   ├── diffPanel.ts            # Diff reviewer webview provider
│   │   └── activityLog.ts          # Activity tree data provider
│   ├── editor/
│   │   └── inlineDecorator.ts      # Inline edit decorations
│   └── webview/
│       ├── taskPanelContent.ts     # Task panel HTML/CSS/JS
│       ├── specsPanelContent.ts    # Specs panel HTML/CSS/JS
│       └── diffPanelContent.ts     # Diff panel HTML/CSS/JS
├── media/
│   ├── styles.css                  # Shared stylesheets
│   ├── taskPanel.js                # Task panel scripts
│   └── icons/
│       └── agent.svg               # Activity bar icon
├── package.json                    # Extension manifest
├── tsconfig.json                   # TypeScript configuration
└── README.md                       # This file
```

## WebSocket Event Schema

### Client → Server Messages

#### Control Messages
```json
{
  "type": "control",
  "action": "pause|resume|stop"
}
```

#### Review Messages
```json
{
  "type": "review",
  "action": "approve|reject|request-changes",
  "feedback": "string (optional, for request-changes)"
}
```

#### Spec Messages
```json
{
  "type": "specs",
  "action": "regenerate"
}
```

### Server → Client Messages

#### Task Update
```json
{
  "type": "task_update",
  "payload": {
    "id": "string",
    "name": "string",
    "state": "Planning|Generating|Testing|Fixing|AwaitingReview|Complete|Failed",
    "progress": 0-100,
    "startTime": "number (ms)",
    "endTime": "number (ms, optional)",
    "error": "string (optional)",
    "logs": ["string"]
  }
}
```

#### Status Change
```json
{
  "type": "status_change",
  "payload": {
    "state": "string",
    "currentTask": "string (optional)",
    "timestamp": "number (ms)",
    "details": "string (optional)"
  }
}
```

#### Edit Start
```json
{
  "type": "edit_start",
  "payload": {
    "filePath": "string",
    "startLine": "number",
    "endLine": "number",
    "description": "string (optional)"
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
    "error": "string (optional)"
  }
}
```

#### Diff Ready
```json
{
  "type": "diff_ready",
  "payload": {
    "filePath": "string",
    "oldContent": "string",
    "newContent": "string",
    "startLine": "number",
    "endLine": "number"
  }
}
```

#### Error
```json
{
  "type": "error",
  "message": "string"
}
```

## Configuration

### Extension Settings

```json
{
  "codeAlphaAgent.serverUrl": "ws://localhost:8765",
  "codeAlphaAgent.autoApprove": false,
  "codeAlphaAgent.showInlineEdits": true,
  "codeAlphaAgent.diffViewSideBySide": true
}
```

### User Settings
Press `Cmd+,` (or `Ctrl+,` on Windows/Linux) and search for "Code Alpha" to configure.

## Commands

| Command | Shortcut | Description |
|---------|----------|-------------|
| `codeAlphaAgent.activate` | - | Activate the agent |
| `codeAlphaAgent.pause` | `Ctrl+Shift+Alt+P` | Pause current task |
| `codeAlphaAgent.resume` | `Ctrl+Shift+Alt+R` | Resume paused task |
| `codeAlphaAgent.stop` | `Ctrl+Shift+Alt+X` | Stop all tasks |
| `codeAlphaAgent.approveChanges` | - | Approve pending changes |
| `codeAlphaAgent.rejectChanges` | - | Reject pending changes |
| `codeAlphaAgent.requestChanges` | - | Request modifications |
| `codeAlphaAgent.regenerateSpecs` | - | Regenerate all specs |
| `codeAlphaAgent.editRequirements` | - | Edit requirements spec |
| `codeAlphaAgent.viewSpecHistory` | - | View spec version history |

## Installation

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd extension
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Compile TypeScript**
   ```bash
   npm run compile
   ```

4. **Run in development mode**
   ```bash
   code --extensionDevelopmentPath=. --new-window
   ```

### Production Build

```bash
npm run build
npm run vscode:prepublish
```

## Integration with Code Alpha Backend

### WebSocket Server Setup

The extension expects a WebSocket server running at `ws://localhost:8765` (configurable).

```python
# Python backend example
import asyncio
import json
from websockets import serve

async def handle_client(websocket, path):
    # Send task updates
    await websocket.send(json.dumps({
        "type": "task_update",
        "payload": {
            "id": "task-1",
            "name": "Generate Code",
            "state": "Generating",
            "progress": 45,
            "startTime": 1234567890,
            "logs": ["Starting code generation...", "Created helper function"]
        }
    }))

    # Listen for client messages
    async for message in websocket:
        data = json.loads(message)
        if data["type"] == "control":
            print(f"Action: {data['action']}")

async def main():
    async with serve(handle_client, "localhost", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
```

## Styling

The extension uses VS Code theme colors and respects the current color theme.

### CSS Variables
- `--vscode-foreground`: Main text color
- `--vscode-editor-background`: Editor background
- `--vscode-button-background`: Button color
- `--vscode-panel-border`: Border color

For custom themes, edit `media/styles.css`.

## Troubleshooting

### WebSocket Connection Issues
- Verify the backend server is running at the configured URL
- Check firewall rules allowing WebSocket connections
- Review console output: `View → Output → Code Alpha Agent`

### Inline Edits Not Showing
- Enable "Show Inline Edits" in settings
- Check that files being edited are open in the editor
- Verify file paths match exactly

### Specs Not Saving
- Check write permissions in the workspace
- Verify workspace storage is available
- Review VS Code output panel for errors

## Extension API

### State Manager

```typescript
import { StateManager } from './state/stateManager';

const stateManager = new StateManager(context);

// Update task
stateManager.updateTask({
  id: 'task-1',
  name: 'Generate',
  state: 'Generating',
  progress: 50,
  startTime: Date.now(),
  logs: []
});

// Export/Import state
const exported = stateManager.exportState();
stateManager.importState(exported);
```

### Inline Decorator

```typescript
import { InlineEditDecorator } from './editor/inlineDecorator';

const decorator = new InlineEditDecorator();

// Mark edit in progress
decorator.markEditStart('/path/to/file.ts', 10, 20);

// Mark complete (auto-highlights for 3 seconds)
decorator.markEditComplete('/path/to/file.ts');

// Clear all
decorator.clearAll();
```

## Contributing

1. Follow the existing code structure
2. Use TypeScript for type safety
3. Test webview changes in VS Code
4. Ensure WebSocket messages match the schema
5. Update documentation for new features

## License

MIT License - See LICENSE file for details

## Links

- [VS Code Extension API](https://code.visualstudio.com/api)
- [WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [Code Alpha Documentation](../README.md)
