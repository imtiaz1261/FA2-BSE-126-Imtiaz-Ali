import * as vscode from 'vscode';
import { StateManager, Task } from '../state/stateManager';

export class ActivityLogEntry extends vscode.TreeItem {
  constructor(
    label: string,
    collapsibleState: vscode.TreeItemCollapsibleState,
    public data: any
  ) {
    super(label, collapsibleState);
  }
}

/**
 * Tree data provider for activity log
 * Displays tasks and events in a tree structure
 */
export class ActivityLogProvider implements vscode.TreeDataProvider<ActivityLogEntry> {
  private _onDidChangeTreeData: vscode.EventEmitter<ActivityLogEntry | undefined | null | void> =
    new vscode.EventEmitter<ActivityLogEntry | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<ActivityLogEntry | undefined | null | void> =
    this._onDidChangeTreeData.event;

  private stateManager: StateManager;

  constructor(stateManager: StateManager) {
    this.stateManager = stateManager;

    // Auto-refresh when tasks change
    setInterval(() => this.refresh(), 1000);
  }

  getTreeItem(element: ActivityLogEntry): vscode.TreeItem {
    return element;
  }

  getChildren(element?: ActivityLogEntry): Thenable<ActivityLogEntry[]> {
    if (!element) {
      // Root level: show tasks
      return Promise.resolve(this.getRootItems());
    } else if (element.data.type === 'task') {
      // Task level: show logs
      return Promise.resolve(this.getTaskLogs(element.data.task));
    }

    return Promise.resolve([]);
  }

  /**
   * Get root level items (tasks)
   */
  private getRootItems(): ActivityLogEntry[] {
    const tasks = this.stateManager.getTasks();
    
    return tasks.map(task => {
      const icon = this.getStateIcon(task.state);
      const entry = new ActivityLogEntry(
        `${icon} ${task.name}`,
        task.logs.length > 0 
          ? vscode.TreeItemCollapsibleState.Collapsed 
          : vscode.TreeItemCollapsibleState.None,
        { type: 'task', task }
      );

      entry.description = `${task.progress}% • ${task.state}`;
      entry.tooltip = `Status: ${task.state}\nProgress: ${task.progress}%\nLogs: ${task.logs.length}`;
      
      // Add context menu
      entry.contextValue = 'task';

      return entry;
    });
  }

  /**
   * Get task logs
   */
  private getTaskLogs(task: Task): ActivityLogEntry[] {
    return task.logs.map((log, index) => {
      const entry = new ActivityLogEntry(
        log,
        vscode.TreeItemCollapsibleState.None,
        { type: 'log', index }
      );

      entry.contextValue = 'log';
      entry.command = {
        title: 'Copy Log',
        command: 'codeAlphaAgent.copyLog',
        arguments: [log],
      };

      return entry;
    });
  }

  /**
   * Get icon based on task state
   */
  private getStateIcon(state: string): string {
    switch (state) {
      case 'Planning':
        return '$(lightbulb)';
      case 'Generating':
        return '$(sync~spin)';
      case 'Testing':
        return '$(beaker)';
      case 'Fixing':
        return '$(wrench)';
      case 'AwaitingReview':
        return '$(eye)';
      case 'Complete':
        return '$(check)';
      case 'Failed':
        return '$(error)';
      default:
        return '$(dash)';
    }
  }

  /**
   * Refresh tree
   */
  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  /**
   * Reveal task in tree
   */
  revealTask(taskId: string) {
    const task = this.stateManager.getTask(taskId);
    if (task) {
      const entry = new ActivityLogEntry(
        task.name,
        vscode.TreeItemCollapsibleState.Expanded,
        { type: 'task', task }
      );
      this.reveal(entry, { select: true, focus: true, expand: true });
    }
  }
}
