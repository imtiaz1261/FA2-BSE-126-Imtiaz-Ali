import * as vscode from 'vscode';

/**
 * Manages inline decorations showing real-time edits
 * Displays which lines the agent is currently editing
 */
export class InlineEditDecorator {
  private decorationTypes: Map<string, vscode.TextEditorDecorationType> = new Map();
  private activeDecorations: Map<string, any> = new Map();

  constructor() {
    this.createDecorationTypes();
  }

  /**
   * Create decoration types
   */
  private createDecorationTypes() {
    // Edit in progress decoration
    this.decorationTypes.set('editing', vscode.window.createTextEditorDecorationType({
      backgroundColor: new vscode.ThemeColor('editorCodeLens.foreground'),
      isWholeLine: true,
      light: {
        backgroundColor: '#fffacd80',
        border: '1px solid #ffbb00',
      },
      dark: {
        backgroundColor: '#4a3f0080',
        border: '1px solid #ffbb00',
      },
      gutterIconPath: this.getGutterIconPath('editing'),
      gutterIconSize: '100%',
    }));

    // Edit completed decoration
    this.decorationTypes.set('completed', vscode.window.createTextEditorDecorationType({
      backgroundColor: new vscode.ThemeColor('testing.coverLineBackground'),
      isWholeLine: true,
      light: {
        backgroundColor: '#c6f6d580',
        border: '1px solid #00aa00',
      },
      dark: {
        backgroundColor: '#0d3d1280',
        border: '1px solid #00aa00',
      },
      gutterIconPath: this.getGutterIconPath('completed'),
      gutterIconSize: '100%',
    }));

    // Error decoration
    this.decorationTypes.set('error', vscode.window.createTextEditorDecorationType({
      backgroundColor: new vscode.ThemeColor('editorError.background'),
      isWholeLine: true,
      light: {
        backgroundColor: '#ff664480',
        border: '1px solid #ff0000',
      },
      dark: {
        backgroundColor: '#66000080',
        border: '1px solid #ff0000',
      },
      gutterIconPath: this.getGutterIconPath('error'),
      gutterIconSize: '100%',
    }));

    // Cursor position decoration (subtle)
    this.decorationTypes.set('cursor', vscode.window.createTextEditorDecorationType({
      backgroundColor: new vscode.ThemeColor('editor.lineHighlightBackground'),
      isWholeLine: false,
      light: {
        backgroundColor: '#00000010',
        borderLeft: '3px solid #0066cc',
      },
      dark: {
        backgroundColor: '#ffffff10',
        borderLeft: '3px solid #0066cc',
      },
    }));
  }

  /**
   * Get gutter icon path
   */
  private getGutterIconPath(type: string): string {
    // In production, return actual SVG paths
    // For now, we use VS Code built-in icons
    return '';
  }

  /**
   * Mark edit start
   */
  markEditStart(filePath: string, startLine: number, endLine: number) {
    this.applyDecoration(filePath, startLine, endLine, 'editing');
  }

  /**
   * Mark edit as complete
   */
  markEditComplete(filePath: string) {
    // Change decoration from editing to completed
    const key = `${filePath}:active`;
    const decoration = this.activeDecorations.get(key);
    if (decoration) {
      const editor = decoration.editor;
      const ranges = decoration.ranges;
      
      editor.setDecorations(this.decorationTypes.get('editing')!, []);
      editor.setDecorations(this.decorationTypes.get('completed')!, ranges);

      // Remove after 3 seconds
      setTimeout(() => {
        editor.setDecorations(this.decorationTypes.get('completed')!, []);
        this.activeDecorations.delete(key);
      }, 3000);
    }
  }

  /**
   * Mark edit with error
   */
  markEditError(filePath: string, startLine: number, endLine: number, error: string) {
    this.applyDecoration(filePath, startLine, endLine, 'error', error);
  }

  /**
   * Clear all decorations
   */
  clearAll() {
    this.activeDecorations.forEach((decoration, _key) => {
      decoration.editor.setDecorations(decoration.type, []);
    });
    this.activeDecorations.clear();
  }

  /**
   * Apply decoration to file
   */
  private async applyDecoration(
    filePath: string,
    startLine: number,
    endLine: number,
    decorationType: string,
    message?: string
  ) {
    try {
      const uri = vscode.Uri.file(filePath);
      const editor = vscode.window.activeTextEditor;

      if (!editor || editor.document.uri.fsPath !== filePath) {
        // Try to find the editor for this file
        const editors = vscode.window.visibleTextEditors;
        const targetEditor = editors.find(e => e.document.uri.fsPath === filePath);

        if (!targetEditor) {
          // Open the file
          const doc = await vscode.workspace.openTextDocument(uri);
          const newEditor = await vscode.window.showTextDocument(doc, vscode.ViewColumn.One);
          this.applyDecorationToEditor(
            newEditor,
            startLine,
            endLine,
            decorationType,
            message
          );
          return;
        }

        this.applyDecorationToEditor(targetEditor, startLine, endLine, decorationType, message);
        return;
      }

      this.applyDecorationToEditor(editor, startLine, endLine, decorationType, message);
    } catch (error) {
      console.error('Failed to apply decoration:', error);
    }
  }

  /**
   * Apply decoration to specific editor
   */
  private applyDecorationToEditor(
    editor: vscode.TextEditor,
    startLine: number,
    endLine: number,
    decorationType: string,
    message?: string
  ) {
    const decoration = this.decorationTypes.get(decorationType);
    if (!decoration) {
      return;
    }

    const ranges: vscode.Range[] = [];
    for (let i = startLine; i < endLine; i++) {
      const line = editor.document.lineAt(i);
      ranges.push(new vscode.Range(
        new vscode.Position(i, 0),
        new vscode.Position(i, line.text.length)
      ));
    }

    const decorationOptions: vscode.DecorationOptions[] = ranges.map(range => ({
      range,
      hoverMessage: message || `Edited by Code Alpha agent`,
    }));

    editor.setDecorations(decoration, decorationOptions);

    // Store reference for later manipulation
    const key = `${editor.document.uri.fsPath}:${decorationType}`;
    this.activeDecorations.set(key, {
      editor,
      type: decoration,
      ranges,
      decorationType,
    });
  }

  /**
   * Highlight cursor position
   */
  highlightCursorPosition(editor: vscode.TextEditor, line: number, column: number) {
    const decoration = this.decorationTypes.get('cursor');
    if (!decoration) {
      return;
    }

    const position = new vscode.Position(line, column);
    const range = new vscode.Range(position, position.translate(0, 1));

    editor.setDecorations(decoration, [{ range }]);

    // Auto-scroll to show the cursor
    editor.revealRange(range, vscode.TextEditorRevealType.InCenter);
  }

  /**
   * Dispose decorations
   */
  dispose() {
    this.decorationTypes.forEach(type => type.dispose());
    this.decorationTypes.clear();
  }
}
