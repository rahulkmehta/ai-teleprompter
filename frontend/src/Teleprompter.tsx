import { useEffect, useMemo, useRef } from 'react';
import type { ScriptStatus } from './types';

const WORD_RE = /[a-zA-Z0-9]+(?:'[a-zA-Z0-9]+)*/g;
const VIEWPORT_LOOKAHEAD = 0.25;

type TeleprompterProps = {
  script: string;
  pointer: number;
  confidence: number;
  status: ScriptStatus;
  onStop: () => void;
};

export function Teleprompter({ script, pointer, confidence, status, onStop }: TeleprompterProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  const words = useMemo(() => {
    const matches = [...script.matchAll(WORD_RE)];
    return matches.map((m) => m[0]);
  }, [script]);

  const atEnd = words.length > 0 && pointer >= words.length;

  useEffect(() => {
    if (!viewportRef.current || !contentRef.current || words.length === 0) return;
    const idx = Math.min(pointer, words.length - 1);
    const wordEl = contentRef.current.querySelector(
      `[data-idx="${idx}"]`
    ) as HTMLElement | null;
    if (!wordEl) return;
    const targetY =
      wordEl.offsetTop - viewportRef.current.clientHeight * VIEWPORT_LOOKAHEAD;
    contentRef.current.style.setProperty('--target-y', `${-targetY}px`);
  }, [pointer, words.length]);

  return (
    <section className={`prompter prompter-${status}${atEnd ? ' prompter-end' : ''}`}>
      <div ref={viewportRef} className="prompter-viewport">
        <div ref={contentRef} className="prompter-content">
          {words.map((w, i) => (
            <span
              key={i}
              data-idx={i}
              className={
                i < pointer
                  ? 'word spoken'
                  : i === pointer
                  ? 'word current'
                  : 'word upcoming'
              }
            >
              {w}{' '}
            </span>
          ))}
        </div>
        {atEnd && <div className="prompter-end-overlay">end of script</div>}
      </div>
      <div className="prompter-controls">
        <span className="recording-dot" aria-hidden="true" />
        <span className={`status status-${status}`}>{status.replace('_', ' ')}</span>
        <span className="confidence">Confidence {(confidence * 100).toFixed(0)}%</span>
        <button onClick={onStop}>Stop</button>
      </div>
    </section>
  );
}
