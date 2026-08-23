import * as vscode from 'vscode';
import { SpecDocument } from '../state/stateManager';

export function getSpecsPanelContent(
  webview: vscode.Webview,
  extensionUri: vscode.Uri,
  specs: { requirements?: SpecDocument; design?: SpecDocument; tasks?: SpecDocument }
): string {
  const styleUri = webview.asWebviewUri(
    vscode.Uri.joinPath(extensionUri, 'media', 'styles.css')
  );
  const nonce = getNonce();

  const requirementsContent = specs.requirements?.content || '';
  const designContent = specs.design?.content || '';
  const tasksContent = specs.tasks?.content || '';

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'">
  <link rel="stylesheet" href="${styleUri}">
  <style>
    .tabs {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--vscode-panel-border);
      margin-bottom: 16px;
    }

    .tab-btn {
      padding: 8px 16px;
      background: transparent;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--vscode-foreground);
      cursor: pointer;
      font-size: 13px;
    }

    .tab-btn.active {
      border-bottom-color: var(--vscode-activityBarBadge-background);
      color: var(--vscode-activityBarBadge-background);
    }

    .tab-content {
      display: none;
    }

    .tab-content.active {
      display: block;
    }

    .editor-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .spec-editor {
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
      font-size: 12px;
      line-height: 1.5;
      padding: 12px;
      background: var(--vscode-editor-background);
      color: var(--vscode-editor-foreground);
      border: 1px solid var(--vscode-panel-border);
      border-radius: 4px;
      min-height: 300px;
      resize: vertical;
    }

    .spec-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: var(--vscode-descriptionForeground);
      padding: 8px 0;
    }

    .spec-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .btn-small {
      padding: 6px 12px;
      font-size: 12px;
    }

    .preview {
      background: var(--vscode-editor-background);
      border: 1px solid var(--vscode-panel-border);
      border-radius: 4px;
      padding: 12px;
      max-height: 400px;
      overflow-y: auto;
    }

    .preview h1, .preview h2, .preview h3 {
      margin-top: 16px;
      margin-bottom: 8px;
    }

    .preview h1 { font-size: 24px; }
    .preview h2 { font-size: 18px; }
    .preview h3 { font-size: 14px; }

    .preview ul, .preview ol {
      margin-left: 20px;
      margin-bottom: 8px;
    }

    .preview code {
      background: var(--vscode-editor-lineHighlightBackground);
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    }
  </style>
  <title>Code Alpha Specs</title>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2>📋 Specifications</h2>
      <div class="spec-actions">
        <button class="btn btn-sm" onclick="regenerateAllSpecs()">
          <i class="codicon codicon-refresh"></i> Regenerate All
        </button>
        <button class="btn btn-sm" onclick="showHistory()">
          <i class="codicon codicon-history"></i> History
        </button>
      </div>
    </div>

    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('requirements')">
        Requirements
      </button>
      <button class="tab-btn" onclick="switchTab('design')">
        Design
      </button>
      <button class="tab-btn" onclick="switchTab('tasks')">
        Tasks
      </button>
    </div>

    <!-- Requirements Tab -->
    <div id="requirements" class="tab-content active">
      <div class="editor-container">
        <div class="spec-meta">
          <span>Requirements v${specs.requirements?.version || 0} • Modified ${specs.requirements?.lastModified ? new Date(specs.requirements.lastModified).toLocaleString() : 'Never'}</span>
          <div class="spec-actions">
            <button class="link-btn" onclick="exportSpec('requirements')">Export</button>
            <button class="link-btn" onclick="importSpec('requirements')">Import</button>
          </div>
        </div>
        <textarea class="spec-editor" id="requirementsEditor" placeholder="Enter project requirements...">${requirementsContent}</textarea>
        <div class="spec-actions">
          <button class="btn btn-sm" onclick="saveSpec('requirements')">
            <i class="codicon codicon-save"></i> Save
          </button>
          <button class="btn btn-sm" onclick="regenerateFrom('requirements')">
            <i class="codicon codicon-refresh"></i> Regenerate From Here
          </button>
        </div>
      </div>
    </div>

    <!-- Design Tab -->
    <div id="design" class="tab-content">
      <div class="editor-container">
        <div class="spec-meta">
          <span>Design v${specs.design?.version || 0} • Modified ${specs.design?.lastModified ? new Date(specs.design.lastModified).toLocaleString() : 'Never'}</span>
          <div class="spec-actions">
            <button class="link-btn" onclick="exportSpec('design')">Export</button>
            <button class="link-btn" onclick="importSpec('design')">Import</button>
          </div>
        </div>
        <div style="display: flex; gap: 12px; height: 400px;">
          <div style="flex: 1; display: flex; flex-direction: column;">
            <label style="font-size: 11px; color: var(--vscode-descriptionForeground); margin-bottom: 4px;">Editor</label>
            <textarea class="spec-editor" id="designEditor" style="flex: 1; min-height: auto;" placeholder="Enter design details...">${designContent}</textarea>
          </div>
          <div style="flex: 1; display: flex; flex-direction: column;">
            <label style="font-size: 11px; color: var(--vscode-descriptionForeground); margin-bottom: 4px;">Preview</label>
            <div class="preview" id="designPreview" style="flex: 1;"></div>
          </div>
        </div>
        <div class="spec-actions">
          <button class="btn btn-sm" onclick="saveSpec('design')">
            <i class="codicon codicon-save"></i> Save
          </button>
          <button class="btn btn-sm" onclick="regenerateFrom('design')">
            <i class="codicon codicon-refresh"></i> Regenerate From Here
          </button>
        </div>
      </div>
    </div>

    <!-- Tasks Tab -->
    <div id="tasks" class="tab-content">
      <div class="editor-container">
        <div class="spec-meta">
          <span>Tasks v${specs.tasks?.version || 0} • Modified ${specs.tasks?.lastModified ? new Date(specs.tasks.lastModified).toLocaleString() : 'Never'}</span>
          <div class="spec-actions">
            <button class="link-btn" onclick="exportSpec('tasks')">Export</button>
            <button class="link-btn" onclick="importSpec('tasks')">Import</button>
          </div>
        </div>
        <textarea class="spec-editor" id="tasksEditor" placeholder="Enter task definitions...">${tasksContent}</textarea>
        <div class="spec-actions">
          <button class="btn btn-sm" onclick="saveSpec('tasks')">
            <i class="codicon codicon-save"></i> Save
          </button>
          <button class="btn btn-sm" onclick="regenerateFrom('tasks')">
            <i class="codicon codicon-refresh"></i> Regenerate From Here
          </button>
        </div>
      </div>
    </div>
  </div>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();

    function switchTab(tabName) {
      // Hide all tabs
      document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.remove('active');
      });
      document.querySelectorAll('.tab-btn').forEach(el => {
        el.classList.remove('active');
      });

      // Show selected tab
      document.getElementById(tabName).classList.add('active');
      event.target.classList.add('active');

      vscode.postMessage({
        type: 'specTabChanged',
        specType: tabName
      });
    }

    function saveSpec(specType) {
      const editor = document.getElementById(specType + 'Editor');
      const content = editor.value;

      vscode.postMessage({
        type: 'specContentChanged',
        specType,
        content
      });

      const btn = event.target;
      const originalText = btn.textContent;
      btn.textContent = '✓ Saved';
      setTimeout(() => {
        btn.textContent = originalText;
      }, 2000);
    }

    function regenerateFrom(specType) {
      vscode.postMessage({
        type: 'regenerateFromHere',
        specType
      });
    }

    function regenerateAllSpecs() {
      vscode.postMessage({ type: 'regenerateClicked' });
    }

    function showHistory() {
      vscode.postMessage({ type: 'showHistory' });
    }

    function exportSpec(specType) {
      vscode.postMessage({ type: 'exportSpec', specType });
    }

    function importSpec(specType) {
      vscode.postMessage({ type: 'importSpec', specType });
    }

    // Live preview for design tab
    const designEditor = document.getElementById('designEditor');
    const designPreview = document.getElementById('designPreview');
    
    if (designEditor && designPreview) {
      designEditor.addEventListener('input', () => {
        // Simple markdown preview simulation
        const md = designEditor.value;
        designPreview.innerHTML = md.split('\\n').map(line => {
          if (line.startsWith('# ')) return '<h1>' + line.substring(2) + '</h1>';
          if (line.startsWith('## ')) return '<h2>' + line.substring(3) + '</h2>';
          if (line.startsWith('### ')) return '<h3>' + line.substring(4) + '</h3>';
          if (line.trim()) return '<p>' + line + '</p>';
          return '';
        }).join('');
      });
    }

    // Handle spec updates from extension
    window.addEventListener('message', event => {
      const message = event.data;
      if (message.type === 'specsUpdate') {
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
