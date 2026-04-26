// Thin WebSocket client used by App.tsx

import type { ScriptStatus, ServerMessage } from './types';

export type WSHandlers = {
  onReady?: (tokenCount: number) => void;
  onPointer?: (index: number, confidence: number, tentative: boolean) => void;
  onTranscript?: (text: string, isFinal: boolean) => void;
  onState?: (status: ScriptStatus) => void;
  onError?: (message: string, recoverable: boolean) => void;
  onClose?: () => void;
};

export class WSClient {
  private ws: WebSocket | null = null;

  constructor(private url: string, private handlers: WSHandlers) {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(this.url);
      ws.binaryType = 'arraybuffer';
      ws.onopen = () => {
        this.ws = ws;
        resolve();
      };
      ws.onerror = () => reject(new Error('WebSocket connection failed'));
      ws.onclose = () => this.handlers.onClose?.();
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as ServerMessage;
          this.dispatch(msg);
        } catch {
          // ignore malformed
        }
      };
    });
  }

  send(msg: object): void {
    this.ws?.send(JSON.stringify(msg));
  }

  sendBinary(data: ArrayBuffer): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    }
  }

  close(): void {
    this.ws?.close();
    this.ws = null;
  }

  private dispatch(msg: ServerMessage): void {
    switch (msg.type) {
      case 'ready':
        this.handlers.onReady?.(msg.token_count);
        break;
      case 'pointer':
        this.handlers.onPointer?.(msg.index, msg.confidence, msg.tentative);
        break;
      case 'transcript':
        this.handlers.onTranscript?.(msg.text, msg.is_final);
        break;
      case 'state':
        this.handlers.onState?.(msg.status);
        break;
      case 'error':
        this.handlers.onError?.(msg.message, msg.recoverable);
        break;
    }
  }
}
