import * as vscode from 'vscode';
import { StateManager, Task } from '../state/stateManager';
import { getWebviewContent } from '../webview/taskPanelContent';

/**
 * Manages the Task Panel webview
 * Displays current task list with live status updates
 */
export class TaskPanelProvider implements vscode.WebviewPanelSerializer {
  private panel: vscode.WebviewPanel | undefined;
  private extensionUri: vscode.Uri;
  private stateManager: StateManager;
  private disposables: vscode.Disposable[] = [];

  constructor(extensionUri: vscode.Uri, stateManager: StateManager) {
    this.extensionUri = extensionUri;
    this.stateManager = stateManager;
  }

  /**
   * Restore webview state (called by VS Code)
   */
  async deserializeWebviewPanel(
    webviewPanel: vscode.WebviewPanel,
    _state: any
  ) {
    this.panel = webviewPanel;
    this.initializePanel();
  }

  /**
   * Show the task panel
   */
  async showPanel() {
    if (this.panel) {
      this.panel.reveal(vscode.ViewColumn.Two);
      return;
    }

    this.panel = vscode.window.createWebviewPanel(
      'codeAlphaTaskPanel',
      'Code Alpha Tasks',
      vscode.ViewColumn.Two,
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
   * Initialize panel
   */
  private initializePanel() {
    if (!this.panel) {
      return;
    }

    this.panel.webview.html = getWebviewContent(
      this.panel.webview,
      this.extensionUri,
      this.getTasksData()
    );

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
   * Refresh task panel display
   */
  refresh() {
    if (this.panel) {
      this.panel.webview.postMessage({
        type: 'tasksUpdate',
        payload: this.getTasksData(),
      });
    }
  }

  /**
   * Handle messages from webview
   */
  private handleWebviewMessage(message: any) {
    switch (message.type) {
      case 'taskClicked':
        this.handleTaskClicked(message.taskId);
        break;
      case 'pauseClicked':
        vscode.commands.executeCommand('codeAlphaAgent.pause');
        break;
      case 'resumeClicked':
        vscode.commands.executeCommand('codeAlphaAgent.resume');
        break;
      case 'stopClicked':
        vscode.commands.executeCommand('codeAlphaAgent.stop');
        break;
    }
  }

  /**
   * Handle task click
   */
  private handleTaskClicked(taskId: string) {
    const task = this.stateManager.getTask(taskId);
    if (task && task.logs.length > 0) {
      const outputChannel = vscode.window.createOutputChannel(`Task: ${task.name}`);
      outputChannel.append(task.logs.join('\n'));
      outputChannel.show();
    }
  }

  /**
   * Get tasks data for webview
   */
  private getTasksData() {
    const tasks = this.stateManager.getTasks();
    const status = this.stateManager.getStatus();

    return {
      tasks: tasks.map(task => ({
        id: task.id,
        name: task.name,
        state: task.state,
        progress: task.progress,
        startTime: new Date(task.startTime).toLocaleString(),
        endTime: task.endTime ? new Date(task.endTime).toLocaleString() : null,
        error: task.error,
        logCount: task.logs.length,
      })),
      status: status ? {
        state: status.state,
        currentTask: status.currentTask,
        details: status.details,
      } : null,
    };
  }
}
