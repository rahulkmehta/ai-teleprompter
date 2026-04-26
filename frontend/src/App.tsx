import { useRef, useState } from 'react';
import { Editor } from './Editor';
import { Teleprompter } from './Teleprompter';
import { PCMCapture } from './audio';
import { WSClient } from './ws';
import type { ScriptStatus } from './types';
import './App.css';

const WS_URL = `ws://${location.host}/ws`;

type AppState = 'idle' | 'starting' | 'recording' | 'stopping';

function App() {
  const [state, setState] = useState<AppState>('idle');
  const [script, setScript] = useState('');
  const [pointer, setPointer] = useState(0);
  const [confidence, setConfidence] = useState(0);
  const [status, setStatus] = useState<ScriptStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WSClient | null>(null);
  const captureRef = useRef<PCMCapture | null>(null);

  const cleanup = async () => {
    await captureRef.current?.stop().catch(() => {});
    wsRef.current?.close();
    captureRef.current = null;
    wsRef.current = null;
  };

  const stop = async () => {
    setState('stopping');
    await cleanup();
    setPointer(0);
    setConfidence(0);
    setStatus('idle');
    setState('idle');
  };

  const start = async () => {
    setError(null);
    setState('starting');
    setPointer(0);
    setConfidence(0);
    setStatus('idle');

    try {
      const ws = new WSClient(WS_URL, {
        onPointer: (index, conf) => {
          setPointer(index);
          setConfidence(conf);
        },
        onState: (s) => setStatus(s),
        onError: (msg, recoverable) => {
          setError(msg);
          if (!recoverable) {
            void stop();
          }
        },
      });
      await ws.connect();
      ws.send({ type: 'init', script });
      wsRef.current = ws;

      const capture = new PCMCapture();
      await capture.start((chunk) => ws.sendBinary(chunk));
      captureRef.current = capture;

      setState('recording');
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      await cleanup();
      setState('idle');
    }
  };

  if (state === 'recording') {
    return (
      <Teleprompter
        script={script}
        pointer={pointer}
        confidence={confidence}
        status={status}
        onStop={stop}
      />
    );
  }

  return (
    <Editor
      script={script}
      onScriptChange={setScript}
      onStart={start}
      error={error}
      busy={state === 'starting' || state === 'stopping'}
    />
  );
}

export default App;
