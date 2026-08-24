import * as vscode from 'vscode';
import { StateManager, SpecDocument } from '../state/stateManager';
import { getSpecsPanelContent } from '../webview/specsPanelContent';

/**
 * Manages the Specs Panel webview
 * Displays and allows editing of requirements.md, design.md, and tasks.md
 */
export class SpecsPanelProvider implements vscode.WebviewPanelSerializer {
  private panel: vscode.WebviewPanel | undefined;
  private extensionUri: vscode.Uri;
  private stateManager: StateManager;
  private disposables: vscode.Disposable[] = [];
  private currentSpecType: 'requirements' | 'design' | 'tasks' = 'requirements';

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
   * Open the specs panel
   */
  async openPanel() {
    if (this.panel) {
      this.panel.reveal(vscode.ViewColumn.Three);
      return;
    }

    this.panel = vscode.window.createWebviewPanel(
      'codeAlphaSpecsPanel',
      'Specs',
      vscode.ViewColumn.Three,
      {
        enableScripts: true,
        enableCommandUris: true,
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

    const specs = {
      requirements: this.stateManager.getSpec('requirements'),
      design: this.stateManager.getSpec('design'),
      tasks: this.stateManager.getSpec('tasks'),
    };

    this.panel.webview.html = getSpecsPanelContent(
      this.panel.webview,
      this.extensionUri,
      specs
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
   * Handle messages from webview
   */
  private async handleWebviewMessage(message: any) {
    switch (message.type) {
      case 'specTabChanged':
        this.currentSpecType = message.specType;
        this.refreshDisplay();
        break;

      case 'specContentChanged':
        this.stateManager.updateSpec(message.specType, message.content);
        this.panel?.webview.postMessage({
          type: 'specSaved',
          specType: message.specType,
        });
        break;

      case 'regenerateClicked':
        await vscode.commands.executeCommand('codeAlphaAgent.regenerateSpecs');
        break;

      case 'regenerateFromHere':
        await this.handleRegenerateFrom(message.specType);
        break;

      case 'showHistory':
        await this.showHistory();
        break;

      case 'exportSpec':
        await this.exportSpec(message.specType);
        break;

      case 'importSpec':
        await this.importSpec(message.specType);
        break;
    }
  }

  /**
   * Handle regenerate from specific spec
   */
  private async handleRegenerateFrom(specType: string) {
    const confirmation = await vscode.window.showWarningMessage(
      `Regenerate ${specType} and all dependent specs? This will overwrite current content.`,
      'Regenerate',
      'Cancel'
    );

    if (confirmation === 'Regenerate') {
      // In a real implementation, this would call the backend API
      vscode.window.showInformationMessage(`Regenerating ${specType}...`);
    }
  }

  /**
   * Show spec version history
   */
  async showHistory() {
    const specs = this.stateManager.getAllSpecs();
    const historyItems = Array.from(specs.values()).map(spec => ({
      label: `${spec.type} v${spec.version}`,
      description: new Date(spec.lastModified).toLocaleString(),
      detail: `${spec.content.length} characters`,
    }));

    const selected = await vscode.window.showQuickPick(historyItems, {
      placeHolder: 'Select a spec version to view',
    });

    if (selected) {
      vscode.window.showInformationMessage(`Viewing: ${selected.label}`);
    }
  }

  /**
   * Export spec to file
   */
  private async exportSpec(specType: string) {
    const spec = this.stateManager.getSpec(specType as any);
    if (!spec) {
      vscode.window.showErrorMessage(`No ${specType} spec found`);
      return;
    }

    const uri = await vscode.window.showSaveDialog({
      defaultUri: vscode.Uri.file(`${specType}.md`),
      filters: {
        'Markdown': ['md'],
        'All Files': ['*'],
      },
    });

    if (uri) {
      const fs = await import('fs').then(m => m.promises);
      try {
        await fs.writeFile(uri.fsPath, spec.content, 'utf-8');
        vscode.window.showInformationMessage(`Exported ${specType} to ${uri.fsPath}`);
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to export: ${error}`);
      }
    }
  }

  /**
   * Import spec from file
   */
  private async importSpec(specType: string) {
    const uris = await vscode.window.showOpenDialog({
      canSelectMany: false,
      filters: {
        'Markdown': ['md'],
        'All Files': ['*'],
      },
    });

    if (uris && uris.length > 0) {
      const fs = await import('fs').then(m => m.promises);
      try {
        const content = await fs.readFile(uris[0].fsPath, 'utf-8');
        this.stateManager.updateSpec(specType as any, content);
        this.refreshDisplay();
        vscode.window.showInformationMessage(`Imported ${specType} from ${uris[0].fsPath}`);
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to import: ${error}`);
      }
    }
  }

  /**
   * Refresh the display
   */
  private refreshDisplay() {
    if (!this.panel) {
      return;
    }

    const specs = {
      requirements: this.stateManager.getSpec('requirements'),
      design: this.stateManager.getSpec('design'),
      tasks: this.stateManager.getSpec('tasks'),
    };

    this.panel.webview.postMessage({
      type: 'specsUpdate',
      currentSpec: this.currentSpecType,
      payload: specs,
    });
  }
}
