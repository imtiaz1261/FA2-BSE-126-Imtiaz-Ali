import * as vscode from 'vscode';

export function getWebviewContent(
  webview: vscode.Webview,
  extensionUri: vscode.Uri,
  data: any
): string {
  const styleUri = webview.asWebviewUri(
    vscode.Uri.joinPath(extensionUri, 'media', 'styles.css')
  );
  const scriptUri = webview.asWebviewUri(
    vscode.Uri.joinPath(extensionUri, 'media', 'taskPanel.js')
  );

  const nonce = getNonce();

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'">
  <link rel="stylesheet" href="${styleUri}">
  <title>Code Alpha Tasks</title>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2>🤖 Code Alpha Agent</h2>
      <div class="status-badge" id="statusBadge">
        ${data.status ? `
          <span class="status-dot" data-state="${data.status.state.toLowerCase()}"></span>
          <span>${data.status.state}</span>
        ` : 'Idle'}
      </div>
    </div>

    <div class="controls">
      <button class="btn btn-sm" id="pauseBtn" onclick="pauseTask()" disabled>
        <i class="codicon codicon-debug-pause"></i> Pause
      </button>
      <button class="btn btn-sm" id="resumeBtn" onclick="resumeTask()" disabled>
        <i class="codicon codicon-debug-continue"></i> Resume
      </button>
      <button class="btn btn-sm btn-danger" id="stopBtn" onclick="stopTask()" disabled>
        <i class="codicon codicon-debug-stop"></i> Stop
      </button>
    </div>

    <div class="tasks-list" id="tasksList">
      ${data.tasks && data.tasks.length > 0 ? 
        data.tasks.map((task: any) => `
          <div class="task-item" data-task-id="${task.id}">
            <div class="task-header">
              <div class="task-title">
                <span class="task-state-icon" data-state="${task.state.toLowerCase()}">
                  ${getStateIcon(task.state)}
                </span>
                <span class="task-name">${task.name}</span>
              </div>
              <div class="task-progress">
                <div class="progress-bar">
                  <div class="progress-fill" style="width: ${task.progress}%"></div>
                </div>
                <span class="progress-text">${task.progress}%</span>
              </div>
            </div>
            <div class="task-details">
              <span class="detail-item">
                <span class="label">State:</span>
                <span class="value">${task.state}</span>
              </span>
              <span class="detail-item">
                <span class="label">Started:</span>
                <span class="value">${task.startTime}</span>
              </span>
              ${task.endTime ? `
                <span class="detail-item">
                  <span class="label">Ended:</span>
                  <span class="value">${task.endTime}</span>
                </span>
              ` : ''}
              ${task.error ? `
                <span class="detail-item error">
                  <span class="label">Error:</span>
                  <span class="value">${task.error}</span>
                </span>
              ` : ''}
              ${task.logCount > 0 ? `
                <button class="link-btn" onclick="viewTaskLogs('${task.id}')">
                  📋 View ${task.logCount} log entries
                </button>
              ` : ''}
            </div>
          </div>
        `).join('')
        : '<div class="empty-state">No tasks yet. Start the agent to begin.</div>'
      }
    </div>
  </div>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();

    function pauseTask() {
      vscode.postMessage({ type: 'pauseClicked' });
    }

    function resumeTask() {
      vscode.postMessage({ type: 'resumeClicked' });
    }

    function stopTask() {
      if (confirm('Are you sure you want to stop the current task?')) {
        vscode.postMessage({ type: 'stopClicked' });
      }
    }

    function viewTaskLogs(taskId) {
      vscode.postMessage({ type: 'taskClicked', taskId });
    }

    // Handle updates from extension
    window.addEventListener('message', event => {
      const message = event.data;
      if (message.type === 'tasksUpdate') {
        location.reload();
      }
    });

    // Update button states based on status
    function updateButtonStates() {
      const statusBadge = document.getElementById('statusBadge');
      const status = statusBadge.textContent.trim();
      
      document.getElementById('pauseBtn').disabled = status !== 'Generating' && status !== 'Testing' && status !== 'Fixing';
      document.getElementById('resumeBtn').disabled = status !== 'AwaitingReview';
      document.getElementById('stopBtn').disabled = status === 'Idle';
    }

    updateButtonStates();
  </script>
</body>
</html>`;
}

function getNonce(): string {
  let text = '';
  const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}

function getStateIcon(state: string): string {
  switch (state) {
    case 'Planning':
      return '💡';
    case 'Generating':
      return '⚙️';
    case 'Testing':
      return '🧪';
    case 'Fixing':
      return '🔧';
    case 'AwaitingReview':
      return '👁️';
    case 'Complete':
      return '✅';
    case 'Failed':
      return '❌';
    default:
      return '⏳';
  }
}
