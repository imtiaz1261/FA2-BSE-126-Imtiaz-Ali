import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

let currentPanel: vscode.WebviewPanel | undefined;
const API_URL = 'http://localhost:8000';

export function activate(context: vscode.ExtensionContext) {
    console.log('✅ Code Alpha Kiro Extension v3 activated!');

    const disposable = vscode.commands.registerCommand(
        'codeAlpha.newTask',
        () => {
            openKiroInterface(context);
        }
    );

    context.subscriptions.push(disposable);
    vscode.window.showInformationMessage('✨ Code Alpha Kiro v3 Ready! Press Ctrl+Shift+K');
}

function openKiroInterface(context: vscode.ExtensionContext) {
    if (currentPanel) {
        currentPanel.reveal(vscode.ViewColumn.Two);
        return;
    }

    currentPanel = vscode.window.createWebviewPanel(
        'kiroInterface',
        '⚡ Code Alpha - Kiro v3',
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

        case 'updateSubTask':
            // Forward to UI
            panel.webview.postMessage(message);
            break;

        case 'createFile':
            await handleCreateFile(message.fileName, message.content, panel);
            break;

        case 'editFile':
            await handleEditFile(message.filePath, message.content, panel);
            break;

        case 'openFile':
            await handleOpenFile(message.filePath, panel);
            break;

        case 'saveFile':
            await handleSaveFile(message.filePath, message.content, panel);
            break;
    }
}

async function handleCreateTask(prompt: string, panel: vscode.WebviewPanel) {
    try {
        const response = await fetch(`${API_URL}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, repo_path: '.' })
        });

        const taskData = await response.json();
        const taskId = taskData.task_id;

        panel.webview.postMessage({
            type: 'taskStarted',
            taskId,
            prompt,
            fileType: taskData.file_type
        });

        // Poll for progress
        await pollTaskProgress(taskId, panel);

    } catch (error) {
        panel.webview.postMessage({
            type: 'error',
            message: `Error: ${error}`
        });
    }
}

async function pollTaskProgress(taskId: string, panel: vscode.WebviewPanel) {
    let isComplete = false;
    let attempts = 0;
    const maxAttempts = 30;

    while (!isComplete && attempts < maxAttempts) {
        try {
            const response = await fetch(`${API_URL}/tasks/${taskId}`);
            const taskData = await response.json();

            panel.webview.postMessage({
                type: 'progressUpdate',
                taskId,
                status: taskData.status,
                subTasks: taskData.sub_tasks,
                generatedCode: taskData.generated_code,
                logs: taskData.logs,
                filePath: taskData.file_path,
                fileType: taskData.file_type
            });

            if (taskData.status === 'complete' || taskData.status === 'completed') {
                isComplete = true;

                // Create file in workspace
                if (taskData.generated_code && taskData.file_path) {
                    const fileName = path.basename(taskData.file_path);
                    await handleCreateFile(fileName, taskData.generated_code, panel);

                    panel.webview.postMessage({
                        type: 'taskComplete',
                        taskId,
                        fileName,
                        filePath: taskData.file_path,
                        code: taskData.generated_code
                    });
                }
            }

            attempts++;
            await new Promise(resolve => setTimeout(resolve, 300));

        } catch (error) {
            attempts++;
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }
}

async function handleCreateFile(fileName: string, content: string, panel: vscode.WebviewPanel) {
    try {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            panel.webview.postMessage({
                type: 'error',
                message: 'No workspace folder open'
            });
            return;
        }

        const filePath = path.join(workspaceFolder.uri.fsPath, fileName);
        fs.writeFileSync(filePath, content, 'utf8');

        // Open file
        const uri = vscode.Uri.file(filePath);
        await vscode.window.showTextDocument(uri);

        panel.webview.postMessage({
            type: 'fileCreated',
            fileName,
            filePath
        });

    } catch (error) {
        panel.webview.postMessage({
            type: 'error',
            message: `Failed to create file: ${error}`
        });
    }
}

async function handleEditFile(filePath: string, content: string, panel: vscode.WebviewPanel) {
    try {
        fs.writeFileSync(filePath, content, 'utf8');
        panel.webview.postMessage({
            type: 'fileUpdated',
            filePath
        });
    } catch (error) {
        panel.webview.postMessage({
            type: 'error',
            message: `Failed to edit file: ${error}`
        });
    }
}

async function handleOpenFile(filePath: string, panel: vscode.WebviewPanel) {
    try {
        const uri = vscode.Uri.file(filePath);
        await vscode.window.showTextDocument(uri);
    } catch (error) {
        panel.webview.postMessage({
            type: 'error',
            message: `Failed to open file: ${error}`
        });
    }
}

async function handleSaveFile(filePath: string, content: string, panel: vscode.WebviewPanel) {
    try {
        fs.writeFileSync(filePath, content, 'utf8');
        panel.webview.postMessage({
            type: 'fileSaved',
            filePath
        });
    } catch (error) {
        panel.webview.postMessage({
            type: 'error',
            message: `Failed to save file: ${error}`
        });
    }
}

function getWebviewContent(): string {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Alpha - Kiro v3</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1e1e1e;
            color: #e0e0e0;
            padding: 15px;
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .header {
            text-align: center;
            margin-bottom: 15px;
            border-bottom: 2px solid #0ea5e9;
            padding-bottom: 10px;
        }

        .header h1 {
            color: #0ea5e9;
            font-size: 18px;
        }

        .main {
            display: flex;
            flex-direction: column;
            flex: 1;
            gap: 10px;
            min-height: 0;
        }

        .section {
            background: #252525;
            border: 1px solid #404040;
            border-radius: 6px;
            padding: 12px;
            flex-shrink: 0;
        }

        .section.flex {
            flex: 1;
            min-height: 0;
            display: flex;
            flex-direction: column;
        }

        textarea {
            width: 100%;
            background: #1e1e1e;
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 4px;
            padding: 8px;
            font-family: monospace;
            resize: none;
            height: 50px;
        }

        textarea:focus {
            outline: none;
            border-color: #0ea5e9;
        }

        button {
            background: #0ea5e9;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
        }

        button:hover {
            background: #0284c7;
        }

        button:disabled {
            background: #666;
            cursor: not-allowed;
        }

        .input-group {
            display: flex;
            gap: 8px;
        }

        .input-group textarea {
            flex: 1;
            height: auto;
        }

        .progress-list {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .sub-task {
            background: #1e1e1e;
            border-left: 3px solid #666;
            padding: 8px;
            border-radius: 3px;
            font-size: 12px;
        }

        .sub-task.running {
            border-left-color: #f59e0b;
            background: rgba(245, 158, 11, 0.05);
        }

        .sub-task.complete {
            border-left-color: #10b981;
            background: rgba(16, 185, 129, 0.05);
        }

        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .status.running {
            background: rgba(245, 158, 11, 0.2);
            color: #fcd34d;
        }

        .status.complete {
            background: rgba(16, 185, 129, 0.2);
            color: #86efac;
        }

        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
        }

        .tab {
            padding: 6px 12px;
            background: #1e1e1e;
            border: 1px solid #404040;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            color: #888;
        }

        .tab.active {
            background: #252525;
            color: #0ea5e9;
            border-color: #0ea5e9;
        }

        pre {
            background: #1e1e1e;
            padding: 10px;
            border-radius: 4px;
            overflow-y: auto;
            flex: 1;
            font-size: 11px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .spinner {
            display: inline-block;
            width: 8px;
            height: 8px;
            border: 2px solid #f59e0b;
            border-right-color: transparent;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
            margin-right: 4px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ Code Alpha - Kiro v3</h1>
        <p style="font-size: 11px; color: #888; margin-top: 3px;">Smart code generation with real-time progress</p>
    </div>

    <div class="main">
        <div class="section">
            <div class="input-group">
                <textarea id="taskInput" placeholder="Describe your task... (e.g., 'Create an HTML page')"></textarea>
                <button id="executeBtn" onclick="executeTask()" style="width: 90px; height: 50px;">⚡<br>EXECUTE</button>
            </div>
        </div>

        <div class="section flex">
            <div id="statusBadge" class="status">READY</div>
            <div style="font-size: 12px; color: #0ea5e9; margin-bottom: 6px;">📋 Task Execution</div>
            <div class="progress-list" id="progressList">
                <div style="color: #888; font-size: 12px;">Ready for input...</div>
            </div>
        </div>

        <div class="section flex">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('logs')">📋 Logs</div>
                <div class="tab" onclick="switchTab('code')">💻 Code</div>
            </div>
            <pre id="logsTab"><code>Waiting for task...</code></pre>
            <pre id="codeTab" style="display: none;"><code>Code output here...</code></pre>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        async function executeTask() {
            const task = document.getElementById('taskInput').value.trim();
            if (!task) {
                alert('Enter a task description');
                return;
            }

            document.getElementById('executeBtn').disabled = true;
            document.getElementById('statusBadge').textContent = 'EXECUTING...';
            document.getElementById('statusBadge').className = 'status running';
            document.getElementById('progressList').innerHTML = '';

            vscode.postMessage({
                command: 'createTask',
                prompt: task
            });
        }

        function switchTab(tab) {
            const logsTab = document.getElementById('logsTab');
            const codeTab = document.getElementById('codeTab');
            const tabs = document.querySelectorAll('.tab');

            if (tab === 'logs') {
                logsTab.style.display = 'block';
                codeTab.style.display = 'none';
                tabs[0].classList.add('active');
                tabs[1].classList.remove('active');
            } else {
                logsTab.style.display = 'none';
                codeTab.style.display = 'block';
                tabs[0].classList.remove('active');
                tabs[1].classList.add('active');
            }
        }

        window.addEventListener('message', event => {
            const msg = event.data;

            switch (msg.type) {
                case 'taskStarted':
                    document.getElementById('progressList').innerHTML = '';
                    break;

                case 'progressUpdate':
                    updateProgress(msg);
                    break;

                case 'taskComplete':
                    onComplete(msg);
                    break;

                case 'error':
                    onError(msg.message);
                    break;
            }
        });

        function updateProgress(data) {
            const list = document.getElementById('progressList');
            
            // Update sub-tasks
            if (data.subTasks) {
                list.innerHTML = data.subTasks.map(st => \`
                    <div class="sub-task \${st.status}">
                        <div style="display: flex; gap: 4px; align-items: center;">
                            \${st.status === 'running' ? '<span class="spinner"></span>' : st.status === 'complete' ? '✓' : '⏳'}
                            <span>\${st.name}</span>
                        </div>
                    </div>
                \`).join('');
            }

            // Update logs
            if (data.logs) {
                document.getElementById('logsTab').innerHTML = \`<code>\${data.logs.join('\\n')}</code>\`;
            }

            // Update code
            if (data.generatedCode) {
                const codeEl = document.getElementById('codeTab');
                codeEl.innerHTML = \`<code class="language-\${data.fileType}\">\${escapeHtml(data.generatedCode)}</code>\`;
                hljs.highlightElement(codeEl.querySelector('code'));
            }
        }

        function onComplete(data) {
            document.getElementById('statusBadge').textContent = 'COMPLETE ✅';
            document.getElementById('statusBadge').className = 'status complete';
            document.getElementById('executeBtn').disabled = false;

            alert('✅ File created: ' + data.fileName);
        }

        function onError(error) {
            document.getElementById('statusBadge').textContent = 'ERROR ❌';
            document.getElementById('executeBtn').disabled = false;
            alert('Error: ' + error);
        }

        function escapeHtml(text) {
            return text.replace(/[<>&"']/g, char => ({
                '<': '&lt;',
                '>': '&gt;',
                '&': '&amp;',
                '"': '&quot;',
                "'": '&#39;'
            }[char]));
        }
    </script>
</body>
</html>
    `;
}

export function deactivate() { }
