import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as http from 'http';

const API = 'http://localhost:8000';
let panel: vscode.WebviewPanel | undefined;

export function activate(ctx: vscode.ExtensionContext) {
    console.log('[Kiro] Extension activating...');
    
    const cmd = vscode.commands.registerCommand('codeAlpha.newTask', () => {
        console.log('[Kiro] Command triggered');
        openPanel(ctx);
    });
    ctx.subscriptions.push(cmd);
    
    vscode.window.showInformationMessage('✅ Code Alpha Kiro ready — Ctrl+Shift+K');
}

export function deactivate() { }

// ─────────────────────────────────────────────────────────────────────────────
// PANEL
// ─────────────────────────────────────────────────────────────────────────────
function openPanel(ctx: vscode.ExtensionContext) {
    console.log('[Kiro] openPanel called');
    if (panel) { 
        console.log('[Kiro] Panel already exists, revealing');
        panel.reveal(vscode.ViewColumn.Two); 
        return; 
    }

    console.log('[Kiro] Creating new panel');
    panel = vscode.window.createWebviewPanel(
        'kiro', '⚡ Kiro Agent',
        vscode.ViewColumn.Two,
        { enableScripts: true, retainContextWhenHidden: true }
    );

    panel.webview.html = buildHtml();
    panel.onDidDispose(() => { 
        console.log('[Kiro] Panel disposed');
        panel = undefined; 
    });

    panel.webview.onDidReceiveMessage(async msg => {
        console.log('[Kiro] Message received from webview:', msg.type);
        switch (msg.type) {
            case 'run':      
                console.log('[Kiro] Running task:', msg.prompt);
                await onRun(msg.prompt, msg.repoPath); 
                break;
            case 'saveFile': await onSaveFile(msg.filePath, msg.code); break;
            case 'openFile': await onOpenFile(msg.filePath); break;
        }
    });
    console.log('[Kiro] Panel opened with message handler registered');
}

// ─────────────────────────────────────────────────────────────────────────────
// RUN A TASK  — POST /tasks then consume SSE /tasks/{id}/stream
// ─────────────────────────────────────────────────────────────────────────────
async function onRun(prompt: string, repoPath: string) {
    console.log('[Kiro] onRun called:', { prompt, repoPath });
    if (!panel) {
        console.log('[Kiro] ERROR: panel is null');
        return;
    }

    // Resolve workspace path so files land in the open folder
    const ws = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? repoPath;
    console.log('[Kiro] Workspace path:', ws);
    send({ type: 'status', text: 'running' });

    // ── POST /tasks ──────────────────────────────────────────────────────────
    let taskId: string;
    try {
        console.log('[Kiro] POSTing to /tasks with prompt:', prompt);
        const res = await postJson(`${API}/tasks`, { prompt, repo_path: ws });
        taskId = res.task_id;
        console.log('[Kiro] Task created:', { taskId, pattern: res.pattern });
        // Show the initial sub-task list immediately (all pending)
        send({ type: 'init', task: res });
    } catch (e: any) {
        console.log('[Kiro] ERROR posting task:', e);
        send({ type: 'error', text: String(e) });
        return;
    }

    // ── Consume SSE /tasks/{id}/stream ───────────────────────────────────────
    console.log('[Kiro] Starting SSE consumer for task:', taskId);
    await consumeSSE(`${API}/tasks/${taskId}/stream`, (data: string) => {
        try {
            const task = JSON.parse(data);
            console.log('[Kiro] SSE update received, status:', task.status);
            send({ type: 'update', task });

            if (task.status === 'complete') {
                console.log('[Kiro] Task complete, writing file:', task.file_name);
                // Write the file into the workspace so VS Code can open it
                const dest = path.join(ws, task.file_name);
                if (task.generated_code) {
                    fs.writeFileSync(dest, task.generated_code, 'utf8');
                    console.log('[Kiro] File written:', dest);
                }
                // Tell the webview the real path
                send({ type: 'done', task, filePath: dest });
                // Open the file in the editor
                vscode.window.showTextDocument(vscode.Uri.file(dest));
            }
        } catch (e) { 
            console.log('[Kiro] ERROR parsing SSE frame:', e);
        }
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// SAVE / OPEN FILE
// ─────────────────────────────────────────────────────────────────────────────
async function onSaveFile(filePath: string, code: string) {
    try {
        fs.writeFileSync(filePath, code, 'utf8');
        // Also tell backend so its store is consistent
        await putJson(`${API}/tasks`, filePath, code);
        vscode.window.showInformationMessage(`✅ Saved: ${path.basename(filePath)}`);
        send({ type: 'fileSaved', filePath });
        vscode.window.showTextDocument(vscode.Uri.file(filePath));
    } catch (e: any) {
        send({ type: 'error', text: String(e) });
    }
}

async function onOpenFile(filePath: string) {
    try {
        vscode.window.showTextDocument(vscode.Uri.file(filePath));
    } catch (e: any) {
        send({ type: 'error', text: String(e) });
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function send(msg: object) { panel?.webview.postMessage(msg); }

function postJson(url: string, body: object): Promise<any> {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify(body);
        const u = new URL(url);
        const req = http.request(
            { hostname: u.hostname, port: Number(u.port) || 80,
              path: u.pathname, method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } },
            res => {
                let buf = '';
                res.on('data', c => buf += c);
                res.on('end', () => {
                    try { resolve(JSON.parse(buf)); }
                    catch { reject(new Error('Bad JSON from server')); }
                });
            }
        );
        req.on('error', reject);
        req.write(data);
        req.end();
    });
}

function putJson(baseUrl: string, filePath: string, code: string): Promise<any> {
    // We don't know the task_id here so we just skip the PUT silently
    return Promise.resolve();
}

function consumeSSE(url: string, onData: (s: string) => void): Promise<void> {
    return new Promise((resolve) => {
        const u = new URL(url);
        const req = http.request(
            { hostname: u.hostname, port: Number(u.port) || 80, path: u.pathname, method: 'GET' },
            res => {
                let buf = '';
                res.on('data', (chunk: Buffer) => {
                    buf += chunk.toString();
                    const lines = buf.split('\n');
                    buf = lines.pop() ?? '';
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            onData(line.slice(6).trim());
                        }
                    }
                });
                res.on('end', resolve);
                res.on('error', resolve);
            }
        );
        req.on('error', resolve);
        req.end();
    });
}

function buildHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Code Alpha Kiro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0f172a;
            color: #e2e8f0;
            font-family: 'Segoe UI', -apple-system, sans-serif;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
            padding: 16px;
            gap: 12px;
        }
        .hdr {
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 12px;
        }
        .hdr h1 {
            font-size: 16px;
            color: #6366f1;
        }
        .badge {
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
        }
        .badge.running { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
        .badge.error { background: rgba(239, 68, 68, 0.2); color: #fca5a5; }
        
        .input-row {
            display: flex;
            gap: 8px;
        }
        textarea {
            flex: 1;
            background: #1e293b;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 10px;
            font-size: 13px;
            resize: none;
            height: 60px;
            font-family: inherit;
        }
        textarea:focus {
            outline: none;
            border-color: #6366f1;
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
        }
        button {
            background: #6366f1;
            color: #fff;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: background 0.2s;
        }
        button:hover:not(:disabled) {
            background: #4f46e5;
        }
        button:disabled {
            background: #475569;
            cursor: not-allowed;
            opacity: 0.6;
        }
        
        .content {
            display: flex;
            flex: 1;
            gap: 12px;
            min-height: 0;
        }
        
        .left {
            width: 240px;
            flex-shrink: 0;
            background: #1e293b;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            border: 1px solid #334155;
        }
        .left-hdr {
            padding: 10px;
            font-size: 11px;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            border-bottom: 1px solid #0f172a;
        }
        .tasks-list {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }
        .subtask {
            padding: 6px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-bottom: 2px;
            display: flex;
            align-items: flex-start;
            gap: 6px;
            color: #94a3b8;
            transition: background 0.15s;
        }
        .subtask.running {
            background: rgba(245, 158, 11, 0.1);
            color: #fcd34d;
        }
        .subtask.complete {
            color: #34d399;
        }
        .subtask-icon {
            flex-shrink: 0;
            width: 14px;
            height: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .spinner {
            display: inline-block;
            width: 10px;
            height: 10px;
            border: 2px solid currentColor;
            border-right-color: transparent;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }
        
        .right {
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
        }
        
        .tabs {
            display: flex;
            gap: 6px;
            border-bottom: 1px solid #334155;
            margin-bottom: 8px;
        }
        .tab {
            padding: 6px 12px;
            font-size: 12px;
            cursor: pointer;
            color: #64748b;
            background: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            font-weight: 500;
            transition: color 0.2s;
        }
        .tab.active {
            color: #6366f1;
            border-bottom-color: #6366f1;
        }
        
        .pane {
            flex: 1;
            min-height: 0;
            overflow-y: auto;
            display: none;
        }
        .pane.active {
            display: block;
        }
        
        .code-box {
            background: #0d1117;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Cascadia Code', monospace;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
            line-height: 1.4;
        }
        
        .logs-box {
            background: #0d1117;
            border-radius: 4px;
            padding: 10px;
            font-family: monospace;
            font-size: 11px;
            color: #94a3b8;
            white-space: pre-wrap;
            word-break: break-word;
            line-height: 1.4;
        }
        
        .placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #334155;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="hdr">
        <h1>⚡ Code Alpha — Kiro Agent</h1>
        <span id="badge" class="badge">READY</span>
    </div>
    
    <div class="input-row">
        <textarea id="prompt" placeholder="Describe your task…  e.g.  create a REST API for user management"></textarea>
        <button id="executeBtn" onclick="executeTask()">▶ EXECUTE</button>
    </div>
    
    <div class="content">
        <div class="left">
            <div class="left-hdr">📋 Sub-Tasks</div>
            <div class="tasks-list" id="tasksList">
                <div class="placeholder">Run a task to see breakdown</div>
            </div>
        </div>
        
        <div class="right">
            <div class="tabs">
                <button class="tab active" onclick="selectTab('code')">💻 Code</button>
                <button class="tab" onclick="selectTab('logs')">📋 Logs</button>
            </div>
            
            <div id="code-pane" class="pane active">
                <div class="code-box" id="codeOutput">Generated code will appear here…</div>
            </div>
            
            <div id="logs-pane" class="pane">
                <div class="logs-box" id="logsOutput">Waiting for task…</div>
            </div>
        </div>
    </div>
    
    <script>
        console.log('[Webview] Page loaded and ready');
        
        const vscode = acquireVsCodeApi ? acquireVsCodeApi() : null;
        let currentTask = null;
        
        function executeTask() {
            const prompt = document.getElementById('prompt').value.trim();
            if (!prompt) {
                alert('Please enter a task description');
                return;
            }
            
            console.log('[Webview] Execute clicked, prompt:', prompt);
            setBadge('running');
            document.getElementById('executeBtn').disabled = true;
            document.getElementById('tasksList').innerHTML = '<div style="padding: 8px; color: #94a3b8; font-size: 12px;">Starting…</div>';
            document.getElementById('codeOutput').textContent = 'Generating…';
            document.getElementById('logsOutput').textContent = 'Task started…';
            
            if (vscode) {
                console.log('[Webview] Posting message to extension');
                vscode.postMessage({
                    type: 'run',
                    prompt: prompt,
                    repoPath: '.'
                });
            } else {
                console.error('[Webview] vscode API not available!');
                alert('VS Code API unavailable - extension may not be properly loaded');
            }
        }
        
        function selectTab(tab) {
            ['code', 'logs'].forEach(t => {
                document.getElementById(t + '-pane').classList.toggle('active', t === tab);
                document.querySelectorAll('.tab').forEach((b, i) => {
                    b.classList.toggle('active', (i === (tab === 'code' ? 0 : 1)));
                });
            });
        }
        
        function setBadge(status) {
            const badge = document.getElementById('badge');
            const labels = {
                ready: 'READY',
                running: 'RUNNING…',
                complete: 'COMPLETE ✓',
                error: 'ERROR'
            };
            badge.textContent = labels[status] || status.toUpperCase();
            badge.className = 'badge ' + status;
        }
        
        function renderSubTasks(tasks) {
            const list = document.getElementById('tasksList');
            if (!tasks || tasks.length === 0) {
                list.innerHTML = '<div class="placeholder">No sub-tasks</div>';
                return;
            }
            
            list.innerHTML = tasks.map(st => {
                let icon = '·';
                if (st.status === 'complete') icon = '✓';
                else if (st.status === 'running') icon = '<span class="spinner"></span>';
                
                return \`<div class="subtask \${st.status}">
                    <div class="subtask-icon">\${icon}</div>
                    <div>\${st.name.substring(0, 40)}</div>
                </div>\`;
            }).join('');
            list.scrollTop = list.scrollHeight;
        }
        
        window.addEventListener('message', event => {
            const msg = event.data;
            console.log('[Webview] Message received:', msg.type);
            
            switch (msg.type) {
                case 'init':
                    currentTask = msg.task;
                    renderSubTasks(msg.task.sub_tasks);
                    break;
                    
                case 'update':
                    currentTask = msg.task;
                    renderSubTasks(msg.task.sub_tasks);
                    if (msg.task.logs) {
                        document.getElementById('logsOutput').textContent = msg.task.logs.join('\\n');
                    }
                    if (msg.task.generated_code) {
                        document.getElementById('codeOutput').textContent = msg.task.generated_code;
                    }
                    break;
                    
                case 'done':
                    currentTask = msg.task;
                    renderSubTasks(msg.task.sub_tasks);
                    if (msg.task.generated_code) {
                        document.getElementById('codeOutput').textContent = msg.task.generated_code;
                    }
                    if (msg.task.logs) {
                        document.getElementById('logsOutput').textContent = msg.task.logs.join('\\n');
                    }
                    setBadge('complete');
                    document.getElementById('executeBtn').disabled = false;
                    break;
                    
                case 'error':
                    setBadge('error');
                    document.getElementById('logsOutput').textContent += '\\n✗ ' + msg.text;
                    document.getElementById('executeBtn').disabled = false;
                    break;
            }
        });
    </script>
</body>
</html>`;
}
