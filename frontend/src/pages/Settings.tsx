import { useEffect, useState } from "react";
import { api, type RuntimeSettings } from "../api/client";
import type { Suggestion } from "../api/types";
import { Loading, Pill } from "../components/ui";
import { useAsync, useStoredString } from "../hooks";

const NUMERIC: { key: keyof RuntimeSettings; label: string; step: number; help: string }[] = [
  { key: "confidence_threshold", label: "Konfidenz-Schwelle", step: 0.05, help: "Darunter entscheidet immer ein Mensch." },
  { key: "holdout_rate", label: "Holdout-Quote", step: 0.05, help: "Zufallsanteil, der trotz positiver Empfehlung an Menschen geht." },
  { key: "fairness_gap_threshold", label: "Max. Gruppenlücke", step: 0.05, help: "Ab dieser Lücke gibt es einen Alarm im Modell-Eval." },
  { key: "low_retrieval_threshold", label: "KB-Lücken-Schwelle", step: 0.05, help: "Ähnlichkeit darunter gilt als nicht abgedeckt." },
  { key: "min_group_share", label: "Min. Gruppenanteil", step: 0.01, help: "Darunter gilt eine Gruppe als unterrepräsentiert." },
  { key: "top_k", label: "Top-k Quellen", step: 1, help: "Anzahl abgerufener KB-Abschnitte." },
];

export default function Settings() {
  const settings = useAsync(api.settings);
  const status = useAsync(api.status);
  const [form, setForm] = useState<RuntimeSettings>();
  const [msg, setMsg] = useState<string>();

  useEffect(() => { if (settings.data) setForm(settings.data); }, [settings.data]);

  async function save() {
    if (!form) return;
    try {
      setForm(await api.saveSettings(form));
      setMsg("Gespeichert.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    }
  }

  async function reindex() {
    setMsg("Indexiere …");
    try {
      const r = await api.ingest();
      setMsg(`${r.chunks} Abschnitte mit ${r.embedder} indexiert.`);
      void status.reload();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="grid-2">
      <div className="card stack">
        <h3>Laufzeit-Einstellungen</h3>
        <Loading error={settings.error} loading={!form} />
        {form && (
          <>
            <label>
              Standard-Provider
              <select value={form.default_provider ?? ""} onChange={(e) => setForm({ ...form, default_provider: e.target.value })}>
                {status.data?.providers.map((p) => <option key={p.name} value={p.name}>{p.name} · {p.model}</option>)}
              </select>
            </label>
            <label>
              Provider für LLM-Judge
              <select value={form.judge_provider ?? ""} onChange={(e) => setForm({ ...form, judge_provider: e.target.value || null })}>
                <option value="">wie Standard-Provider</option>
                {status.data?.providers.map((p) => <option key={p.name} value={p.name}>{p.name} · {p.model}</option>)}
              </select>
            </label>
            {NUMERIC.map((n) => (
              <label key={n.key}>
                {n.label}
                <input type="number" step={n.step} min={0} max={n.key === "top_k" ? 10 : 1} value={Number(form[n.key])}
                  onChange={(e) => setForm({ ...form, [n.key]: Number(e.target.value) })} />
                <small>{n.help}</small>
              </label>
            ))}
            <button className="primary" onClick={save}>Speichern</button>
          </>
        )}
        {msg && <p className="muted">{msg}</p>}
      </div>
      <div className="stack">
        <div className="card stack">
          <h3>Wissensbasis</h3>
          <p>{status.data ? `${status.data.chunks} Abschnitte · Embeddings: ${status.data.embedder}` : "…"}</p>
          <small>Quelle: <code>backend/data/kb/*.md</code> (inkl. freigegebener Vorschläge in <code>vorschlaege/</code>)</small>
          <button onClick={reindex}>Neu indexieren</button>
        </div>
        <Suggestions />
      </div>
    </div>
  );
}

function Suggestions() {
  const list = useAsync(() => api.suggestions("pending"));
  const [reviewer, setReviewer] = useStoredString("reviewer", "");
  return (
    <div className="card stack">
      <h3>KB-Vorschläge (Phase 6)</h3>
      <small>Entstehen aus negativem Feedback oder schwachem Retrieval. Nichts wird automatisch gelernt. Ein Mensch schreibt den Text und gibt ihn frei.</small>
      <label>Dein Name<input value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label>
      <Loading error={list.error} loading={list.loading && !list.data} />
      {list.data?.length === 0 && <p className="muted">Keine offenen Vorschläge.</p>}
      {list.data?.map((s) => <SuggestionItem key={s.id} s={s} reviewer={reviewer} onDone={list.reload} />)}
    </div>
  );
}

function SuggestionItem({ s, reviewer, onDone }: { s: Suggestion; reviewer: string; onDone: () => void }) {
  const [text, setText] = useState("");
  const [topic, setTopic] = useState(s.topic ?? "");
  const [err, setErr] = useState<string>();
  async function decide(approve: boolean) {
    try {
      await api.decideSuggestion(s.id, { approve, reviewer, topic: topic || null, text: approve ? text : null });
      onDone();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <div className="source stack" style={{ gap: 6 }}>
      <div className="row"><Pill tone="warning">{s.reason.replace(/_/g, " ")}</Pill><small>{new Date(s.created_at).toLocaleString("de-DE")}</small></div>
      <div className="pre">{s.question}</div>
      <label>Thema<input value={topic} onChange={(e) => setTopic(e.target.value)} /></label>
      <label>KB-Text (von dir verfasst)<textarea value={text} onChange={(e) => setText(e.target.value)} /></label>
      {err && <p className="error">{err}</p>}
      <div className="row">
        <button className="primary" disabled={!text.trim() || !reviewer.trim()} onClick={() => decide(true)}>Freigeben & indexieren</button>
        <button disabled={!reviewer.trim()} onClick={() => decide(false)}>Ablehnen</button>
      </div>
    </div>
  );
}
