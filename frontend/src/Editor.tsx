type EditorProps = {
  script: string;
  onScriptChange: (value: string) => void;
  onStart: () => void;
  error: string | null;
  busy: boolean;
};

export function Editor({ script, onScriptChange, onStart, error, busy }: EditorProps) {
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
        {busy ? 'Starting…' : 'Read Back Script'}
      </button>
    </section>
  );
}
