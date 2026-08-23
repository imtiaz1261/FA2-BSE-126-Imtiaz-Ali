import * as vscode from 'vscode';
import { Diff } from '../state/stateManager';

export function getDiffPanelContent(
  webview: vscode.Webview,
  extensionUri: vscode.Uri,
  diff: Diff
): string {
  const styleUri = webview.asWebviewUri(
    vscode.Uri.joinPath(extensionUri, 'media', 'styles.css')
  );
  const nonce = getNonce();

  // Calculate line numbers
  const oldLines = diff.oldContent.split('\n');
  const newLines = diff.newContent.split('\n');

  // Simple diff algorithm (in production, use a proper diff library)
  const diffLines = computeDiff(oldLines, newLines);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'">
  <link rel="stylesheet" href="${styleUri}">
  <style>
    .diff-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px;
      background: var(--vscode-editor-background);
      border-bottom: 1px solid var(--vscode-panel-border);
      margin-bottom: 16px;
    }

    .file-path {
      font-family: monospace;
      font-size: 12px;
      color: var(--vscode-descriptionForeground);
    }

    .diff-container {
      display: flex;
      gap: 12px;
      height: 500px;
      margin-bottom: 16px;
    }

    .diff-pane {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .pane-header {
      font-size: 12px;
      font-weight: 600;
      padding: 8px 12px;
      background: var(--vscode-editor-lineHighlightBackground);
      border-bottom: 1px solid var(--vscode-panel-border);
    }

    .diff-content {
      flex: 1;
      overflow-y: auto;
      overflow-x: auto;
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
      font-size: 12px;
      line-height: 1.5;
    }

    .diff-line {
      display: flex;
      border-bottom: 1px solid var(--vscode-panel-border);
    }

    .line-number {
      width: 50px;
      padding: 0 8px;
      text-align: right;
      color: var(--vscode-descriptionForeground);
      background: var(--vscode-editor-lineNumberActiveForeground);
      user-select: none;
      border-right: 1px solid var(--vscode-panel-border);
    }

    .line-content {
      flex: 1;
      padding: 0 8px;
      white-space: pre-wrap;
      word-break: break-all;
    }

    .line-removed {
      background: rgba(255, 0, 0, 0.1);
    }

    .line-removed .line-content {
      color: #ff6b6b;
    }

    .line-added {
      background: rgba(0, 255, 0, 0.1);
    }

    .line-added .line-content {
      color: #51cf66;
    }

    .line-context {
      background: var(--vscode-editor-background);
    }

    .line-context .line-content {
      color: var(--vscode-editor-foreground);
    }

    .line-marker {
      width: 24px;
      text-align: center;
      font-weight: bold;
      user-select: none;
    }

    .actions {
      display: flex;
      gap: 8px;
      padding: 12px;
      border-top: 1px solid var(--vscode-panel-border);
      background: var(--vscode-editor-background);
    }

    .actions button {
      flex: 1;
    }

    .review-note {
      padding: 12px;
      background: var(--vscode-inputValidation-infoBorder);
      border-left: 3px solid var(--vscode-inputValidation-infoBorder);
      margin-bottom: 12px;
      border-radius: 4px;
    }

    .copy-btn {
      padding: 4px 8px;
      font-size: 11px;
      margin-top: 8px;
    }
  </style>
  <title>Code Changes Review</title>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2>👁️ Review Changes</h2>
      <button class="btn btn-sm" onclick="openFile()">
        <i class="codicon codicon-go-to-file"></i> Open File
      </button>
    </div>

    <div class="review-note">
      <strong>Agent has proposed changes</strong> • Review carefully and approve or request modifications
    </div>

    <div class="diff-header">
      <div class="file-path">${diff.filePath}</div>
      <div style="font-size: 11px; color: var(--vscode-descriptionForeground);">
        Lines ${diff.startLine + 1}–${diff.endLine + 1}
      </div>
    </div>

    <div class="diff-container">
      <div class="diff-pane">
        <div class="pane-header">Before</div>
        <div class="diff-content">
          ${oldLines.map((line, idx) => `
            <div class="diff-line line-removed">
              <div class="line-number">${idx + 1}</div>
              <div class="line-marker">−</div>
              <div class="line-content">${escapeHtml(line)}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="diff-pane">
        <div class="pane-header">After</div>
        <div class="diff-content">
          ${newLines.map((line, idx) => `
            <div class="diff-line line-added">
              <div class="line-number">${idx + 1}</div>
              <div class="line-marker">+</div>
              <div class="line-content">${escapeHtml(line)}</div>
            </div>
          `).join('')}
        </div>
      </div>
    </div>

    <div class="actions">
      <button class="btn btn-success" onclick="approveChanges()">
        <i class="codicon codicon-check"></i> Approve
      </button>
      <button class="btn btn-warning" onclick="requestChanges()">
        <i class="codicon codicon-comment"></i> Request Changes
      </button>
      <button class="btn btn-danger" onclick="rejectChanges()">
        <i class="codicon codicon-close"></i> Reject
      </button>
    </div>

    <div style="padding: 12px; font-size: 11px; color: var(--vscode-descriptionForeground);">
      💡 Tip: Click "Request Changes" to provide specific feedback to the agent
    </div>
  </div>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const filePath = '${diff.filePath}';
    const oldContent = \`${diff.oldContent.replace(/\`/g, '\\\\`')}\`;
    const newContent = \`${diff.newContent.replace(/\`/g, '\\\\`')}\`;

    function approveChanges() {
      if (confirm('Approve these changes?')) {
        vscode.postMessage({ type: 'approveClicked' });
      }
    }

    function rejectChanges() {
      const reason = prompt('Why are you rejecting these changes?');
      if (reason !== null) {
        vscode.postMessage({ 
          type: 'rejectClicked',
          reason 
        });
      }
    }

    function requestChanges() {
      vscode.postMessage({ type: 'requestChangesClicked' });
    }

    function openFile() {
      vscode.postMessage({ 
        type: 'openFileClicked',
        filePath 
      });
    }

    function copyOld() {
      vscode.postMessage({
        type: 'copyOldClicked',
        content: oldContent
      });
    }

    function copyNew() {
      vscode.postMessage({
        type: 'copyNewClicked',
        content: newContent
      });
    }

    function escapeHtml(text) {
      const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
      };
      return text.replace(/[&<>"']/g, m => map[m]);
    }

    // Handle diff updates from extension
    window.addEventListener('message', event => {
      const message = event.data;
      if (message.type === 'diffUpdate') {
        location.reload();
      }
    });
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

function computeDiff(oldLines: string[], newLines: string[]): any[] {
  // Simple diff computation (in production, use a library like diff-match-patch)
  const result = [];
  const maxLen = Math.max(oldLines.length, newLines.length);

  for (let i = 0; i < maxLen; i++) {
    const oldLine = oldLines[i] || '';
    const newLine = newLines[i] || '';

    if (oldLine === newLine) {
      result.push({ type: 'context', line: oldLine, lineNum: i + 1 });
    } else if (!newLine) {
      result.push({ type: 'removed', line: oldLine, lineNum: i + 1 });
    } else if (!oldLine) {
      result.push({ type: 'added', line: newLine, lineNum: i + 1 });
    } else {
      result.push({ type: 'removed', line: oldLine, lineNum: i + 1 });
      result.push({ type: 'added', line: newLine, lineNum: i + 1 });
    }
  }

  return result;
}
