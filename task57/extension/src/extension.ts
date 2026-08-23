import * as vscode from 'vscode';
import { AgentWebSocketClient } from './websocket/client';
import { TaskPanelProvider } from './panels/taskPanel';
import { SpecsPanelProvider } from './panels/specsPanel';
import { DiffPanelProvider } from './panels/diffPanel';
import { ActivityLogProvider } from './panels/activityLog';
import { InlineEditDecorator } from './editor/inlineDecorator';
import { StateManager } from './state/stateManager';

let extensionContext: vscode.ExtensionContext;
let wsClient: AgentWebSocketClient;
let stateManager: StateManager;
let taskPanel: TaskPanelProvider;
let specsPanel: SpecsPanelProvider;
let diffPanel: DiffPanelProvider;
let activityLog: ActivityLogProvider;
let inlineDecorator: InlineEditDecorator;

export async function activate(context: vscode.ExtensionContext) {
  extensionContext = context;
  
  console.log('Activating Code Alpha Agent extension...');

  // Initialize state manager
  stateManager = new StateManager(context);

  // Initialize inline edit decorator
  inlineDecorator = new InlineEditDecorator();

  // Initialize panel providers
  taskPanel = new TaskPanelProvider(context.extensionUri, stateManager);
  specsPanel = new SpecsPanelProvider(context.extensionUri, stateManager);
  diffPanel = new DiffPanelProvider(context.extensionUri, stateManager);
  activityLog = new ActivityLogProvider(stateManager);

  // Register webview panel providers
  context.subscriptions.push(
    vscode.window.registerWebviewPanelSerializer('codeAlphaTaskPanel', taskPanel),
    vscode.window.registerWebviewPanelSerializer('codeAlphaSpecsPanel', specsPanel),
    vscode.window.registerWebviewPanelSerializer('codeAlphaDiffPanel', diffPanel)
  );

  // Register tree data providers
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider('codeAlphaActivityLog', activityLog)
  );

  // Register commands
  registerCommands(context);

  // Initialize WebSocket client
  const config = vscode.workspace.getConfiguration('codeAlphaAgent');
  const serverUrl = config.get<string>('serverUrl') || 'ws://localhost:8765';
  
  wsClient = new AgentWebSocketClient(serverUrl, {
    onTaskUpdate: handleTaskUpdate,
    onStatusChange: handleStatusChange,
    onEditStart: handleEditStart,
    onEditEnd: handleEditEnd,
    onDiffReady: handleDiffReady,
    onError: handleError,
  });

  // Attempt connection
  await wsClient.connect();

  // Set activated context
  vscode.commands.executeCommand('setContext', 'codeAlphaAgent.activated', true);

  console.log('Code Alpha Agent extension activated successfully!');
}

function registerCommands(context: vscode.ExtensionContext) {
  // Activate command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.activate', async () => {
      vscode.commands.executeCommand('setContext', 'codeAlphaAgent.activated', true);
      await wsClient.connect();
    })
  );

  // Pause command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.pause', async () => {
      await wsClient.send({
        type: 'control',
        action: 'pause',
      });
      vscode.commands.executeCommand('setContext', 'codeAlphaAgent.isRunning', false);
      vscode.commands.executeCommand('setContext', 'codeAlphaAgent.isPaused', true);
    })
  );

  // Resume command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.resume', async () => {
      await wsClient.send({
        type: 'control',
        action: 'resume',
      });
      vscode.commands.executeCommand('setContext', 'codeAlphaAgent.isRunning', true);
      vscode.commands.executeCommand('setContext', 'codeAlphaAgent.isPaused', false);
    })
  );

  // Stop command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.stop', async () => {
      await wsClient.send({
        type: 'control',
        action: 'stop',
      });
      vscode.commands.executeCommand('setContext', 'codeAlphaAgent.isRunning', false);
      vscode.commands.executeCommand('setContext', 'codeAlphaAgent.isPaused', false);
    })
  );

  // Approve changes command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.approveChanges', async () => {
      await wsClient.send({
        type: 'review',
        action: 'approve',
      });
      vscode.commands.executeCommand('setContext', 'codeAlphaAgent.hasChanges', false);
    })
  );

  // Reject changes command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.rejectChanges', async () => {
      await wsClient.send({
        type: 'review',
        action: 'reject',
      });
      vscode.commands.executeCommand('setContext', 'codeAlphaAgent.hasChanges', false);
    })
  );

  // Request changes command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.requestChanges', async () => {
      const feedback = await vscode.window.showInputBox({
        placeHolder: 'Describe the changes you request...',
        prompt: 'Provide feedback for the agent',
      });

      if (feedback) {
        await wsClient.send({
          type: 'review',
          action: 'request-changes',
          feedback,
        });
      }
    })
  );

  // Regenerate specs command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.regenerateSpecs', async () => {
      await wsClient.send({
        type: 'specs',
        action: 'regenerate',
      });
    })
  );

  // Edit requirements command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.editRequirements', async () => {
      await specsPanel.openPanel();
    })
  );

  // View spec history command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.viewSpecHistory', async () => {
      await specsPanel.showHistory();
    })
  );

  // Focus activity log command
  context.subscriptions.push(
    vscode.commands.registerCommand('codeAlphaAgent.focusActivityLog', async () => {
      vscode.commands.executeCommand('codeAlphaActivityLog.focus');
    })
  );
}

function handleTaskUpdate(update: any) {
  stateManager.updateTask(update);
  taskPanel.refresh();
}

function handleStatusChange(status: any) {
  stateManager.setStatus(status);
  
  vscode.commands.executeCommand('setContext', 'codeAlphaAgent.isRunning', 
    status.state === 'Planning' || status.state === 'Generating' || 
    status.state === 'Testing' || status.state === 'Fixing'
  );
  vscode.commands.executeCommand('setContext', 'codeAlphaAgent.isPaused', 
    status.state === 'AwaitingReview'
  );
}

function handleEditStart(edit: any) {
  inlineDecorator.markEditStart(edit.filePath, edit.startLine, edit.endLine);
}

function handleEditEnd(edit: any) {
  inlineDecorator.markEditComplete(edit.filePath);
}

function handleDiffReady(diff: any) {
  stateManager.setCurrentDiff(diff);
  vscode.commands.executeCommand('setContext', 'codeAlphaAgent.hasChanges', true);
  diffPanel.show();
}

function handleError(error: Error) {
  vscode.window.showErrorMessage(`Code Alpha Agent Error: ${error.message}`);
}

export function deactivate() {
  if (wsClient) {
    wsClient.disconnect();
  }
}
