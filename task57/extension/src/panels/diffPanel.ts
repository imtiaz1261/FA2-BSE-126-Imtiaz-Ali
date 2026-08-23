import * as vscode from 'vscode';
import { StateManager } from '../state/stateManager';
import { getDiffPanelContent } from '../webview/diffPanelContent';

/**
 * Manages the Diff Panel webview
 * Displays pending changes for review with approve/reject/request-changes actions
 */
export class DiffPanelProvider implements vscode.WebviewPanelSerializer {
  private panel: vscode.WebviewPanel | undefined;
  private extensionUri: vscode.Uri;
  private stateManager: StateManager;
  private disposables: vscode.Disposable[] = [];

  constructor(extensionUri: vscode.Uri, stateManager: StateManager) {
    this.extensionUri = extensionUri;
    this.stateManager = stateManager;
  }

  /**
   * Restore webview state
   */
  async deserializeWebviewPanel(
    webviewPanel: vscode.WebviewPanel,
    _state: any
  ) {
    this.panel = webviewPanel;
    this.initializePanel();
  }

  /**
   * Show the diff panel
   */
  async show() {
    const diff = this.stateManager.getCurrentDiff();
    if (!diff) {
      return;
    }

    if (this.panel) {
      this.panel.reveal(vscode.ViewColumn.Beside);
      this.refreshContent();
      return;
    }

    this.panel = vscode.window.createWebviewPanel(
      'codeAlphaDiffPanel',
      'Proposed Changes',
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [
          vscode.Uri.joinPath(this.extensionUri, 'media'),
        ],
      }
    );

    this.initializePanel();
  }

  /**
   * Initialize the panel
   */
  private initializePanel() {
    if (!this.panel) {
      return;
    }

    const diff = this.stateManager.getCurrentDiff();
    if (!diff) {
      return;
    }

    this.panel.webview.html = getDiffPanelContent(
      this.panel.webview,
      this.extensionUri,
      diff
    );

    this.panel.title = `Changes: ${diff.filePath}`;

    this.panel.onDidDispose(() => {
      this.panel = undefined;
      this.disposables.forEach(d => d.dispose());
    });

    this.panel.webview.onDidReceiveMessage(
      message => this.handleWebviewMessage(message),
      undefined,
      this.disposables
    );
  }

  /**
   * Refresh content
   */
  private refreshContent() {
    if (!this.panel) {
      return;
    }

    const diff = this.stateManager.getCurrentDiff();
    if (!diff) {
      return;
    }

    this.panel.webview.postMessage({
      type: 'diffUpdate',
      payload: {
        filePath: diff.filePath,
        oldContent: diff.oldContent,
        newContent: diff.newContent,
        startLine: diff.startLine,
        endLine: diff.endLine,
      },
    });
  }

  /**
   * Handle messages from webview
   */
  private async handleWebviewMessage(message: any) {
    switch (message.type) {
      case 'approveClicked':
        await vscode.commands.executeCommand('codeAlphaAgent.approveChanges');
        this.close();
        break;

      case 'rejectClicked':
        await vscode.commands.executeCommand('codeAlphaAgent.rejectChanges');
        this.close();
        break;

      case 'requestChangesClicked':
        await vscode.commands.executeCommand('codeAlphaAgent.requestChanges');
        break;

      case 'openFileClicked':
        this.openFile(message.filePath);
        break;

      case 'copyOldClicked':
        await vscode.env.clipboard.writeText(message.content);
        vscode.window.showInformationMessage('Old content copied to clipboard');
        break;

      case 'copyNewClicked':
        await vscode.env.clipboard.writeText(message.content);
        vscode.window.showInformationMessage('New content copied to clipboard');
        break;
    }
  }

  /**
   * Open file in editor
   */
  private async openFile(filePath: string) {
    try {
      const uri = vscode.Uri.file(filePath);
      const doc = await vscode.workspace.openTextDocument(uri);
      await vscode.window.showTextDocument(doc);
    } catch (error) {
      vscode.window.showErrorMessage(`Failed to open file: ${error}`);
    }
  }

  /**
   * Close the diff panel
   */
  private close() {
    this.panel?.dispose();
    this.panel = undefined;
  }
}
