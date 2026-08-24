import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

let currentPanel: vscode.WebviewPanel | undefined;
const API_URL = 'http://localhost:8000';

export function activate(context: vscode.ExtensionContext) {
    console.log('✅ Code Alpha Kiro Extension activated!');

    // Main command: Open Kiro Interface
    const disposable = vscode.commands.registerCommand(
        'codeAlpha.newTask',
        () => {
            openKiroInterface(context);
        }
    );

    context.subscriptions.push(disposable);
    vscode.window.showInformationMessage('✨ Code Alpha Kiro Ready! Press Ctrl+Shift+K to open');
}

function openKiroInterface(context: vscode.ExtensionContext) {
    if (currentPanel) {
        currentPanel.reveal(vscode.ViewColumn.Two);
        return;
    }

    currentPanel = vscode.window.createWebviewPanel(
        'kiroInterface',
        '⚡ Code Alpha - Task Agent',
        vscode.ViewColumn.Two,
        {
            enableScripts: true,
            enableForms: true,
            retainContextWhenHidden: true
        }
    );

    currentPanel.webview.html = getWebviewContent();

    currentPanel.onDidDispose(() => {
        currentPanel = undefined;
    });

    // Handle messages from webview
    currentPanel.webview.onDidReceiveMessage(async (message) => {
        await handleWebviewMessage(message, context, currentPanel!);
    });
}

async function handleWebviewMessage(
    message: any,
    context: vscode.ExtensionContext,
    panel: vscode.WebviewPanel
) {
    switch (message.command) {
        case 'createTask':
            await handleCreateTask(message.prompt, panel);
            break;

        case 'createFile':
            await handleCreateFile(message.fileName, message.content);
            break;

        case 'updateFile':
            await handleUpdateFile(message.filePath, message.content);
            break;

        case 'openFile':
            await handleOpenFile(message.filePath);
            break;

        case 'logMessage':
            console.log('[Webview]', message.text);
            break;
    }
}

async function handleCreateTask(prompt: string, panel: vscode.WebviewPanel) {
    try {
        // 1. Send request to backend
        const response = await fetch(`${API_URL}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, repo_path: '.' })
        });

        const taskData = await response.json();
        const taskId = taskData.task_id;

        // 2. Update UI with task started
        panel.webview.postMessage({
            type: 'taskStarted',
            taskId,
            prompt
        });

        // 3. Stream task progress
        await streamTaskProgress(taskId, panel);

    } catch (error) {
        panel.webview.postMessage({
            type: 'error',
            message: `Error: ${error}`
        });
    }
}

async function streamTaskProgress(taskId: string, panel: vscode.WebviewPanel) {
    try {
        // Poll for task status
        let isComplete = false;
        let attempts = 0;
        const maxAttempts = 60;

        while (!isComplete && attempts < maxAttempts) {
            const response = await fetch(`${API_URL}/tasks/${taskId}`);
            const taskData = await response.json();

            // Send progress update to webview
            panel.webview.postMessage({
                type: 'progressUpdate',
                taskId,
                status: taskData.status,
                generatedCode: taskData.generated_code,
                logs: taskData.logs || []
            });

            if (taskData.status === 'complete' || taskData.status === 'completed') {
                isComplete = true;

                // Create file with generated code
                if (taskData.generated_code) {
                    const fileName = `task_${taskId}.py`;
                    await handleCreateFile(fileName, taskData.generated_code);

                    panel.webview.postMessage({
                        type: 'taskComplete',
                        taskId,
                        fileName,
                        code: taskData.generated_code
                    });
                }
            }

            attempts++;
            await new Promise(resolve => setTimeout(resolve, 500));
        }

    } catch (error) {
        panel.webview.postMessage({
            type: 'error',
            message: `Streaming error: ${error}`
        });
    }
}

async function handleCreateFile(fileName: string, content: string) {
    try {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }

        const filePath = path.join(workspaceFolder.uri.fsPath, fileName);
        fs.writeFileSync(filePath, content, 'utf8');

        // Open file in editor
        const uri = vscode.Uri.file(filePath);
        await vscode.window.showTextDocument(uri);

        vscode.window.showInformationMessage(`✅ Created: ${fileName}`);
    } catch (error) {
        vscode.window.showErrorMessage(`Failed to create file: ${error}`);
    }
}

async function handleUpdateFile(filePath: string, content: string) {
    try {
        fs.writeFileSync(filePath, content, 'utf8');
        vscode.window.showInformationMessage(`✅ Updated: ${path.basename(filePath)}`);
    } catch (error) {
        vscode.window.showErrorMessage(`Failed to update file: ${error}`);
    }
}

async function handleOpenFile(filePath: string) {
    try {
        const uri = vscode.Uri.file(filePath);
        await vscode.window.showTextDocument(uri);
    } catch (error) {
        vscode.window.showErrorMessage(`Failed to open file: ${error}`);
    }
}

function getWebviewContent(): string {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Alpha - Kiro Task Agent</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #1e1e1e;
            color: #e0e0e0;
            padding: 20px;
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .header {
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #0ea5e9;
            padding-bottom: 15px;
        }

        .header h1 {
            color: #0ea5e9;
            font-size: 24px;
            margin-bottom: 5px;
        }

        .header p {
            color: #888;
            font-size: 12px;
        }

        .main-container {
            display: flex;
            flex-direction: column;
            flex: 1;
            gap: 15px;
            overflow: hidden;
        }

        .task-input-section {
            background: #252525;
            border: 1px solid #404040;
            border-radius: 8px;
            padding: 15px;
        }

        .input-group {
            display: flex;
            gap: 10px;
        }

        textarea {
            flex: 1;
            background: #1e1e1e;
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 4px;
            padding: 10px;
            font-family: monospace;
            resize: vertical;
            min-height: 60px;
        }

        textarea:focus {
            outline: none;
            border-color: #0ea5e9;
            box-shadow: 0 0 10px rgba(14, 165, 233, 0.2);
        }

        button {
            background: #0ea5e9;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.2s;
        }

        button:hover {
            background: #0284c7;
        }

        button:disabled {
            background: #666;
            cursor: not-allowed;
        }

        .progress-section {
            background: #252525;
            border: 1px solid #404040;
            border-radius: 8px;
            padding: 15px;
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }

        .progress-title {
            color: #0ea5e9;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .task-flow {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .sub-task {
            background: #1e1e1e;
            border-left: 3px solid #666;
            padding: 10px;
            border-radius: 4px;
            font-size: 13px;
            transition: all 0.3s;
        }

        .sub-task.running {
            border-left-color: #f59e0b;
            background: rgba(245, 158, 11, 0.1);
        }

        .sub-task.complete {
            border-left-color: #10b981;
            background: rgba(16, 185, 129, 0.1);
        }

        .sub-task.error {
            border-left-color: #ef4444;
            background: rgba(239, 68, 68, 0.1);
        }

        .sub-task-name {
            color: #e0e0e0;
            font-weight: 500;
            margin-bottom: 3px;
        }

        .sub-task-status {
            color: #888;
            font-size: 11px;
            display: flex;
            gap: 5px;
            align-items: center;
        }

        .spinner {
            display: inline-block;
            width: 10px;
            height: 10px;
            border: 2px solid #f59e0b;
            border-right-color: transparent;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .code-section {
            background: #252525;
            border: 1px solid #404040;
            border-radius: 8px;
            padding: 15px;
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
            display: none;
        }

        .code-section.show {
            display: flex;
        }

        .code-section h3 {
            color: #0ea5e9;
            font-size: 14px;
            margin-bottom: 10px;
        }

        pre {
            background: #1e1e1e;
            color: #e0e0e0;
            padding: 12px;
            border-radius: 4px;
            overflow-y: auto;
            flex: 1;
            font-size: 12px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        pre code {
            background: none;
            color: inherit;
            padding: 0;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }

        .tab {
            padding: 8px 15px;
            background: #1e1e1e;
            border: 1px solid #404040;
            border-radius: 4px 4px 0 0;
            cursor: pointer;
            color: #888;
            font-size: 12px;
        }

        .tab.active {
            background: #252525;
            color: #0ea5e9;
            border-bottom-color: #0ea5e9;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .status-badge.pending {
            background: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
        }

        .status-badge.running {
            background: rgba(245, 158, 11, 0.2);
            color: #fcd34d;
        }

        .status-badge.complete {
            background: rgba(16, 185, 129, 0.2);
            color: #86efac;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ Code Alpha - Kiro Task Agent</h1>
        <p>Break down tasks into sub-tasks and execute with real-time progress</p>
    </div>

    <div class="main-container">
        <!-- Task Input -->
        <div class="task-input-section">
            <div class="input-group">
                <textarea 
                    id="taskInput" 
                    placeholder="Describe your task... e.g., 'Create a REST API for user management'"
                ></textarea>
                <button id="executeBtn" onclick="executeTask()">
                    ⚡ EXECUTE
                </button>
            </div>
        </div>

        <!-- Progress & Task Flow -->
        <div class="progress-section">
            <div class="status-badge pending" id="statusBadge">READY</div>
            <div class="progress-title">📋 Task Breakdown & Execution</div>
            <div class="task-flow" id="taskFlow">
                <div style="color: #888; font-size: 12px;">
                    Enter a task and click EXECUTE to break it down into sub-tasks
                </div>
            </div>
        </div>

        <!-- Generated Code -->
        <div class="code-section" id="codeSection">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('logs')">📋 Logs</div>
                <div class="tab" onclick="switchTab('code')">💻 Generated Code</div>
            </div>
            
            <div id="logsTab">
                <pre id="logsContent"><code>Waiting for task execution...</code></pre>
            </div>
            
            <div id="codeTab" style="display: none;">
                <pre id="codeContent"><code>Code will appear here...</code></pre>
            </div>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let currentTaskId = null;

        async function executeTask() {
            const taskInput = document.getElementById('taskInput').value.trim();
            
            if (!taskInput) {
                alert('Please enter a task description');
                return;
            }

            document.getElementById('executeBtn').disabled = true;
            document.getElementById('statusBadge').textContent = 'STARTING...';
            document.getElementById('statusBadge').className = 'status-badge pending';
            document.getElementById('taskFlow').innerHTML = '';
            document.getElementById('codeSection').classList.remove('show');

            // Show initial sub-tasks
            const subTasks = [
                'Analyzing task requirements',
                'Breaking down into sub-tasks',
                'Generating code structure',
                'Implementing functionality',
                'Creating files',
                'Finalizing output'
            ];

            subTasks.forEach(task => {
                addSubTaskUI(task, 'pending');
            });

            // Send to backend
            vscode.postMessage({
                command: 'createTask',
                prompt: taskInput
            });
        }

        function addSubTaskUI(name, status) {
            const taskFlow = document.getElementById('taskFlow');
            const div = document.createElement('div');
            div.className = \`sub-task \${status}\`;
            
            let statusIcon = '⏳';
            let statusText = 'Pending';
            
            if (status === 'running') {
                statusIcon = '<span class="spinner"></span>';
                statusText = 'Running';
            } else if (status === 'complete') {
                statusIcon = '✅';
                statusText = 'Complete';
            } else if (status === 'error') {
                statusIcon = '❌';
                statusText = 'Error';
            }
            
            div.innerHTML = \`
                <div class="sub-task-name">\${name}</div>
                <div class="sub-task-status">\${statusIcon} \${statusText}</div>
            \`;
            
            taskFlow.appendChild(div);
        }

        function switchTab(tab) {
            if (tab === 'logs') {
                document.getElementById('logsTab').style.display = 'block';
                document.getElementById('codeTab').style.display = 'none';
                document.querySelectorAll('.tab')[0].classList.add('active');
                document.querySelectorAll('.tab')[1].classList.remove('active');
            } else {
                document.getElementById('logsTab').style.display = 'none';
                document.getElementById('codeTab').style.display = 'block';
                document.querySelectorAll('.tab')[0].classList.remove('active');
                document.querySelectorAll('.tab')[1].classList.add('active');
            }
        }

        // Handle messages from extension
        window.addEventListener('message', event => {
            const message = event.data;

            switch (message.type) {
                case 'taskStarted':
                    currentTaskId = message.taskId;
                    document.getElementById('statusBadge').textContent = 'EXECUTING...';
                    document.getElementById('statusBadge').className = 'status-badge running';
                    updateSubTaskStatus('Analyzing task requirements', 'running');
                    break;

                case 'progressUpdate':
                    updateProgress(message);
                    break;

                case 'taskComplete':
                    onTaskComplete(message);
                    break;

                case 'error':
                    onTaskError(message.message);
                    break;
            }
        });

        function updateSubTaskStatus(taskName, status) {
            const subTasks = document.querySelectorAll('.sub-task');
            subTasks.forEach(task => {
                if (task.textContent.includes(taskName)) {
                    task.className = \`sub-task \${status}\`;
                }
            });
        }

        function updateProgress(data) {
            const logsContent = document.getElementById('logsContent');
            logsContent.textContent = (data.logs || []).join('\\n') || 'Processing...';

            if (data.generatedCode) {
                document.getElementById('codeContent').textContent = data.generatedCode;
                document.getElementById('codeSection').classList.add('show');
            }
        }

        function onTaskComplete(data) {
            document.getElementById('statusBadge').textContent = 'COMPLETE ✅';
            document.getElementById('statusBadge').className = 'status-badge complete';
            document.getElementById('executeBtn').disabled = false;

            // Update all sub-tasks to complete
            document.querySelectorAll('.sub-task').forEach(task => {
                task.className = 'sub-task complete';
            });

            document.getElementById('codeSection').classList.add('show');
            alert(\`✅ File created: \${data.fileName}\`);
        }

        function onTaskError(error) {
            document.getElementById('statusBadge').textContent = 'ERROR ❌';
            document.getElementById('statusBadge').className = 'status-badge pending';
            document.getElementById('executeBtn').disabled = false;
            alert('Error: ' + error);
        }
    </script>
</body>
</html>
    `;
}

export function deactivate() { }
