// The script-entry view, shown when the app is idle. The user pastes or types
// their script and clicks "Read back" to transition to the Teleprompter view
// (handled by the parent App.tsx).

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
      <h1>Teleprompter</h1>
      {error && <div className="banner banner-error">{error}</div>}
      <textarea
        value={script}
        onChange={(e) => onScriptChange(e.target.value)}
        placeholder="Paste or write your script here..."
        disabled={busy}
      />
      <button onClick={onStart} disabled={!canStart}>
        {busy ? 'Starting…' : 'Read back script'}
      </button>
    </section>
  );
}
