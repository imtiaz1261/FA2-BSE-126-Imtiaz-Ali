# Code Alpha - Kiro-Style VS Code Interface

**Complete autonomous coding interface for VS Code - Like Kiro**

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd kiro_interface
npm install
```

### 2. Build the Extension
```bash
npm run build
```

### 3. Install in VS Code
- Open VS Code
- Press `Ctrl+Shift+P` → "Extensions: Install from VSIX"
- Select the `.vsix` file from `kiro_interface/` directory

### 4. Start Code Alpha Server
```bash
# Terminal 1: Start the Code Alpha API server
cd ..
codealpha api --start

# Or with Docker:
docker-compose up -d
```

### 5. Use the Interface
- Press `Ctrl+Shift+K` to open Code Alpha task input
- Type your coding task
- Click "Run Task"
- Review and approve changes

---

## 📋 Features

### ✅ Kiro-Like Interface
- **Task Input Panel**: Sidebar webview for task assignment
- **Status Bar**: Real-time task status
- **Progress Notifications**: Live task progress
- **Diff Review**: Built-in change review
- **One-Click Approval**: Approve/reject changes easily

### ✅ Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+K` | New Task |
| `Ctrl+Shift+Enter` | Run Task |
| `Ctrl+Shift+R` | Review Changes |
| `Ctrl+Shift+Alt+P` | Pause Task |
| `Ctrl+Shift+Alt+X` | Stop Task |

### ✅ Configuration
- Server URL
- Safety Mode (Permissive/Standard/Strict/Emergency)
- Auto-Approve Changes
- Max Files Per Task
- Enable Notifications

---

## 🎯 Usage

### Create a New Task
1. Press `Ctrl+Shift+K` or click the Code Alpha icon in Activity Bar
2. Type your task description:
   ```
   Create a REST API endpoint for user authentication with JWT tokens
   ```
3. Select options:
   - Safety Mode: Standard
   - Max Files: 50
   - Output Format: JSON
   - Auto-Approve: No
4. Click "▶️ Run Task"

### Monitor Progress
- Status bar shows: `$(hubot) Code Alpha: Running...`
- Output channel shows detailed logs
- Progress notifications appear

### Review Changes
1. Click "Review Changes" button
2. VS Code opens diff view
3. See all modified files
4. Approve or reject changes

---

## 🔧 Configuration

### Settings
Open Settings (`Ctrl+,`) and search for "Code Alpha":

```json
{
  "codeAlpha.serverUrl": "http://localhost:8000",
  "codeAlpha.autoApprove": false,
  "codeAlpha.safetyMode": "standard",
  "codeAlpha.maxFilesPerTask": 50,
  "codeAlpha.enableNotifications": true
}
```

### Server Configuration
The extension connects to Code Alpha API server:
- Default: `http://localhost:8000`
- Configure in Settings or `.vscode/settings.json`

---

## 📊 Architecture

```
┌─────────────────────────────────────────┐
│   VS Code Extension (Kiro Interface)    │
│                                         │
│  ┌──────────────┐  ┌────────────────┐  │
│  │ Task Input   │  │ Status Bar     │  │
│  │ Webview      │  │ Indicator      │  │
│  └──────┬───────┘  └────────────────┘  │
│         │                               │
│  ┌──────▼──────────────────────────┐   │
│  │  Extension Host (TypeScript)    │   │
│  │  - Task Management              │   │
│  │  - Progress Tracking            │   │
│  │  - Change Review                │   │
│  └──────┬──────────────────────────┘   │
└─────────┼───────────────────────────────┘
          │ HTTP/WebSocket
          │
┌─────────▼───────────────────────────────┐
│    Code Alpha API Server (Python)       │
│                                         │
│  - Task Orchestration                   │
│  - Code Generation                      │
│  - Safety Checks                        │
│  - Diff Generation                      │
└─────────────────────────────────────────┘
```

---

## 🧪 Example Tasks

### Code Generation
```
Create a REST API endpoint for user authentication with JWT tokens, 
password hashing, and email validation
```

### Testing
```
Write unit tests for the calculator module with 90% code coverage
```

### Refactoring
```
Refactor the database connection module to use connection pooling 
and async operations
```

### Bug Fixing
```
Fix the bug in payment processing that causes timeout on orders 
with more than 100 items
```

### Documentation
```
Generate comprehensive API documentation for all endpoints in the 
user module with examples
```

---

## 🛠️ Development

### Build
```bash
npm run build
```

### Watch Mode
```bash
npm run watch
```

### Package
```bash
npm run package
```

### Test
```bash
npm test
```

---

## 📦 Project Structure

```
kiro_interface/
├── src/
│   └── extension.ts          # Main extension code
├── media/
│   └── icon.png              # Extension icon
├── out/                      # Compiled code
├── package.json              # Extension manifest
├── tsconfig.json             # TypeScript config
└── README.md                 # This file
```

---

## 🔌 Integration

### With Code Alpha Backend
The extension communicates with Code Alpha API:

**Create Task**
```typescript
POST http://localhost:8000/tasks
{
  "prompt": "Create authentication API",
  "repo_path": "/path/to/repo",
  "options": {
    "safetyMode": "standard",
    "maxFiles": 50
  }
}
```

**Stream Logs**
```typescript
GET http://localhost:8000/tasks/{task_id}/stream
```

**Review Changes**
```typescript
GET http://localhost:8000/tasks/{task_id}/diff
```

**Approve/Reject**
```typescript
POST http://localhost:8000/tasks/{task_id}/approve
POST http://localhost:8000/tasks/{task_id}/reject
```

---

## ✅ Checklist

Before using:

- [ ] Install Node.js 18+
- [ ] Install npm dependencies
- [ ] Build the extension
- [ ] Start Code Alpha API server
- [ ] Configure server URL in Settings
- [ ] Test with simple task

---

## 🆘 Troubleshooting

### "Cannot connect to server"
- Ensure Code Alpha API is running: `codealpha api --start`
- Check server URL in Settings
- Verify port 8000 is not blocked

### "Extension not loading"
- Rebuild extension: `npm run build`
- Check VS Code Output → "Code Alpha"
- Restart VS Code

### "Task failed"
- Check Output Channel for errors
- Verify repository path is correct
- Ensure proper permissions

---

## 🎓 Advanced

### Custom Server URL
```json
{
  "codeAlpha.serverUrl": "https://api.codealpha.example.com"
}
```

### Auto-Approve for CI/CD
```json
{
  "codeAlpha.autoApprove": true,
  "codeAlpha.safetyMode": "permissive"
}
```

### Maximum Files Limit
```json
{
  "codeAlpha.maxFilesPerTask": 100
}
```

---

## 📞 Support

- **Documentation**: See `README.md` files in each module
- **Issues**: Check Output Channel → "Code Alpha"
- **Logs**: View → Output → Code Alpha

---

**Status**: ✅ Production Ready
**Version**: 1.0.0
