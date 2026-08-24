import * as WebSocket from 'ws';

export interface WebSocketEventHandlers {
  onTaskUpdate: (update: any) => void;
  onStatusChange: (status: any) => void;
  onEditStart: (edit: any) => void;
  onEditEnd: (edit: any) => void;
  onDiffReady: (diff: any) => void;
  onError: (error: Error) => void;
}

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

/**
 * Manages WebSocket connection to the Code Alpha orchestrator
 * Handles real-time streaming of agent status, edits, and diffs
 */
export class AgentWebSocketClient {
  private ws: WebSocket | null = null;
  private serverUrl: string;
  private handlers: WebSocketEventHandlers;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private messageQueue: WebSocketMessage[] = [];

  constructor(serverUrl: string, handlers: WebSocketEventHandlers) {
    this.serverUrl = serverUrl;
    this.handlers = handlers;
  }

  /**
   * Connect to the WebSocket server
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.serverUrl);

        this.ws.on('open', () => {
          console.log(`Connected to Code Alpha server at ${this.serverUrl}`);
          this.reconnectAttempts = 0;
          
          // Flush queued messages
          while (this.messageQueue.length > 0) {
            const msg = this.messageQueue.shift();
            if (msg) {
              this.ws!.send(JSON.stringify(msg));
            }
          }
          
          resolve();
        });

        this.ws.on('message', (data: string) => {
          this.handleMessage(data);
        });

        this.ws.on('error', (error: Error) => {
          console.error('WebSocket error:', error);
          this.handlers.onError(error);
          reject(error);
        });

        this.ws.on('close', () => {
          console.log('WebSocket connection closed');
          this.ws = null;
          this.attemptReconnect();
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Handle incoming WebSocket message
   */
  private handleMessage(data: string) {
    try {
      const message: WebSocketMessage = JSON.parse(data);
      
      switch (message.type) {
        case 'task_update':
          this.handlers.onTaskUpdate(message.payload);
          break;
        case 'status_change':
          this.handlers.onStatusChange(message.payload);
          break;
        case 'edit_start':
          this.handlers.onEditStart(message.payload);
          break;
        case 'edit_end':
          this.handlers.onEditEnd(message.payload);
          break;
        case 'diff_ready':
          this.handlers.onDiffReady(message.payload);
          break;
        case 'error':
          this.handlers.onError(new Error(message.message));
          break;
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
      this.handlers.onError(error as Error);
    }
  }

  /**
   * Send message to the server
   */
  async send(message: WebSocketMessage): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.messageQueue.push(message);
      return;
    }

    this.ws.send(JSON.stringify(message));
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.handlers.onError(new Error('Failed to reconnect to Code Alpha server'));
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Attempting to reconnect in ${delay}ms... (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, delay);
  }

  /**
   * Disconnect from the server
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Check if client is connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
