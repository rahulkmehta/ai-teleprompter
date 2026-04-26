// Shared types for messages exchanged with backend/app/api/stream.py.
// Keep in lockstep with backend/app/schemas/messages.py — both sides validate
// against the same shapes.

export type ScriptStatus = 'on_script' | 'off_script' | 'idle';

export type ServerMessage =
  | { type: 'ready'; token_count: number }
  | { type: 'pointer'; index: number; confidence: number; tentative: boolean }
  | { type: 'transcript'; text: string; is_final: boolean }
  | { type: 'state'; status: ScriptStatus }
  | { type: 'error'; message: string; recoverable: boolean };
