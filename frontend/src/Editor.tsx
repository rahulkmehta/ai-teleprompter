// The script-entry view, shown when the app is idle. The user pastes or types
// their script and clicks "Read back" to transition to the Teleprompter view
// (handled by the parent App.tsx). The "Try sample" button populates the
// textarea with a known script so reviewers can demo without typing.

const SAMPLE_SCRIPT = `Hello, my name is Rahul, and this is my AI teleprompter. The interesting parts are how it tracks position when I read perfectly, and how it recovers when I don't. The aligner uses local sequence alignment with phonetic matching and inverse-frequency weighting, so common words don't dominate. If I ad-lib for a moment, the pointer holds. If I skip ahead a sentence, it jumps cleanly. If I mispronounce a rare word, the phonetic fallback still catches it. That's the whole point: the script is the truth, but the reader is human.`;

type Props = {
  script: string;
  onScriptChange: (value: string) => void;
  onStart: () => void;
  error: string | null;
  busy: boolean;
};

export function Editor({ script, onScriptChange, onStart, error, busy }: Props) {
  const canStart = script.trim().length > 0 && !busy;
  return (
    <section className="editor">
      <h1>AI Teleprompter</h1>
      {error && <div className="banner banner-error">{error}</div>}
      <textarea
        value={script}
        onChange={(e) => onScriptChange(e.target.value)}
        placeholder="Paste or write your script here..."
        disabled={busy}
      />
      <div className="editor-actions">
        <button onClick={onStart} disabled={!canStart}>
          {busy ? 'Starting…' : 'Read back script'}
        </button>
        <button
          className="secondary"
          onClick={() => onScriptChange(SAMPLE_SCRIPT)}
          disabled={busy}
        >
          Try sample
        </button>
      </div>
    </section>
  );
}
