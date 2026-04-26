// The reading view. Renders each script word as a positioned span and
// translates the content vertically so the current word sits at ~25% from the
// top of a 4-line viewport. Driven entirely by the `pointer` prop, which the
// parent (App.tsx) updates on each PointerMessage from the backend aligner.
//
// The CSS transition on transform handles the smooth scroll: each pointer
// update sets a new `--target-y` and the browser interpolates. Mid-flight
// target changes are handled gracefully by the transition.

import { useEffect, useMemo, useRef } from 'react';
import type { ScriptStatus } from './types';

const WORD_RE = /[a-zA-Z0-9]+(?:'[a-zA-Z0-9]+)*/g;
const VIEWPORT_LOOKAHEAD = 0.25;

type Props = {
  script: string;
  pointer: number;
  confidence: number;
  status: ScriptStatus;
  onStop: () => void;
};

export function Teleprompter({ script, pointer, confidence, status, onStop }: Props) {
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
        <span className="confidence">conf {(confidence * 100).toFixed(0)}%</span>
        <button onClick={onStop}>Stop</button>
      </div>
    </section>
  );
}
