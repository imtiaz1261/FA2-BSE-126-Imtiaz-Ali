import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export interface Task {
  id: string;
  name: string;
  state: 'Planning' | 'Generating' | 'Testing' | 'Fixing' | 'AwaitingReview' | 'Complete' | 'Failed';
  progress: number; // 0-100
  startTime: number;
  endTime?: number;
  error?: string;
  logs: string[];
}

export interface AgentStatus {
  state: string;
  currentTask?: string;
  timestamp: number;
  details?: string;
}

export interface Diff {
  filePath: string;
  oldContent: string;
  newContent: string;
  startLine: number;
  endLine: number;
}

export interface SpecDocument {
  type: 'requirements' | 'design' | 'tasks';
  content: string;
  version: number;
  lastModified: number;
}

/**
 * Manages the state of the Code Alpha agent
 * Persists to workspace storage for resumability
 */
export class StateManager {
  private tasks: Map<string, Task> = new Map();
  private status: AgentStatus | null = null;
  private currentDiff: Diff | null = null;
  private specs: Map<string, SpecDocument> = new Map();
  private storageKey = 'codeAlphaAgent.state';
  private context: vscode.ExtensionContext;

  constructor(context: vscode.ExtensionContext) {
    this.context = context;
    this.loadFromStorage();
  }

  /**
   * Update a task
   */
  updateTask(task: Task) {
    this.tasks.set(task.id, task);
    this.saveToStorage();
  }

  /**
   * Get a task by ID
   */
  getTask(id: string): Task | undefined {
    return this.tasks.get(id);
  }

  /**
   * Get all tasks
   */
  getTasks(): Task[] {
    return Array.from(this.tasks.values());
  }

  /**
   * Clear all tasks
   */
  clearTasks() {
    this.tasks.clear();
    this.saveToStorage();
  }

  /**
   * Set agent status
   */
  setStatus(status: AgentStatus) {
    this.status = status;
    this.saveToStorage();
  }

  /**
   * Get agent status
   */
  getStatus(): AgentStatus | null {
    return this.status;
  }

  /**
   * Set current diff
   */
  setCurrentDiff(diff: Diff) {
    this.currentDiff = diff;
  }

  /**
   * Get current diff
   */
  getCurrentDiff(): Diff | null {
    return this.currentDiff;
  }

  /**
   * Update spec document
   */
  updateSpec(type: 'requirements' | 'design' | 'tasks', content: string) {
    const existing = this.specs.get(type);
    const version = existing ? existing.version + 1 : 1;
    
    this.specs.set(type, {
      type,
      content,
      version,
      lastModified: Date.now(),
    });

    this.saveToStorage();
  }

  /**
   * Get spec document
   */
  getSpec(type: 'requirements' | 'design' | 'tasks'): SpecDocument | undefined {
    return this.specs.get(type);
  }

  /**
   * Get all specs
   */
  getAllSpecs(): Map<string, SpecDocument> {
    return this.specs;
  }

  /**
   * Add log entry to current task
   */
  addTaskLog(taskId: string, logEntry: string) {
    const task = this.tasks.get(taskId);
    if (task) {
      task.logs.push(`[${new Date().toISOString()}] ${logEntry}`);
      this.saveToStorage();
    }
  }

  /**
   * Save state to extension storage
   */
  private saveToStorage() {
    const state = {
      tasks: Array.from(this.tasks.entries()),
      status: this.status,
      specs: Array.from(this.specs.entries()),
    };

    this.context.globalState.update(this.storageKey, state);
  }

  /**
   * Load state from extension storage
   */
  private loadFromStorage() {
    const state = this.context.globalState.get<any>(this.storageKey);
    
    if (state) {
      if (state.tasks) {
        this.tasks = new Map(state.tasks);
      }
      if (state.status) {
        this.status = state.status;
      }
      if (state.specs) {
        this.specs = new Map(state.specs);
      }
    }
  }

  /**
   * Export state as JSON (for persistence to file)
   */
  exportState(): string {
    return JSON.stringify({
      tasks: Array.from(this.tasks.entries()),
      status: this.status,
      specs: Array.from(this.specs.entries()),
      exportedAt: new Date().toISOString(),
    }, null, 2);
  }

  /**
   * Import state from JSON
   */
  importState(json: string) {
    try {
      const data = JSON.parse(json);
      if (data.tasks) {
        this.tasks = new Map(data.tasks);
      }
      if (data.status) {
        this.status = data.status;
      }
      if (data.specs) {
        this.specs = new Map(data.specs);
      }
      this.saveToStorage();
    } catch (error) {
      console.error('Failed to import state:', error);
      throw error;
    }
  }
}
