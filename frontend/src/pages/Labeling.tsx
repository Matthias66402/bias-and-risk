import { useState } from "react";
import { api } from "../api/client";
import { Loading, RecPill, Sources } from "../components/ui";
import { useAsync, useStoredString } from "../hooks";

export default function Labeling() {
  const [annotator, setAnnotator] = useStoredString("annotator", "");
  const [active, setActive] = useState(annotator);
  const rubric = useAsync(api.rubric);
  const item = useAsync(() => (active ? api.nextLabel(active) : Promise.resolve(null)), [active]);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [comment, setComment] = useState("");
  const [err, setErr] = useState<string>();

  const complete = rubric.data && rubric.data.criteria.every((c) => scores[c.key]);

  async function submit() {
    if (!item.data) return;
    try {
      await api.submitLabel({ interaction_id: item.data.interaction_id, annotator: active, scores, comment: comment || null });
      setScores({});
      setComment("");
      setErr(undefined);
      await item.reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="stack">
      <div className="callout">
        <strong>Phase 3 – Kennzeichnung:</strong> Bewerte Antworten mit der Rubrik <code>{rubric.data?.version}</code>. Du siehst keine Persona-Merkmale (blindes Labeln).
        Jede Antwort soll von mindestens zwei Personen bewertet werden. Die Übereinstimmung erscheint im Dashboard.
      </div>
      <form className="row" onSubmit={(e) => { e.preventDefault(); setActive(annotator.trim()); }}>
        <label>Annotator:in<input value={annotator} onChange={(e) => setAnnotator(e.target.value)} placeholder="z. B. anna" /></label>
        <button className="primary" style={{ alignSelf: "flex-end" }} disabled={!annotator.trim()}>Start</button>
      </form>
      {!active ? null : <Loading error={item.error ?? rubric.error} loading={item.loading} />}
      {active && !item.loading && item.data === null && <p className="muted">Keine offenen Antworten für {active}. Erzeuge Chats oder Eval-Läufe.</p>}
      {item.data && rubric.data && (
        <div className="grid-2">
          <div className="card stack">
            <small>Bereits von {item.data.already_labeled_by} Person(en) bewertet</small>
            <div><h4>Anfrage</h4><div className="pre">{item.data.message}</div></div>
            <div><h4>Antwort</h4><div className="pre">{item.data.answer}</div></div>
            <div className="rec"><h4>Empfehlung</h4><RecPill type={item.data.recommendation.type} /> <small>{item.data.recommendation.rationale}</small></div>
            <Sources sources={item.data.sources} />
          </div>
          <div className="card stack">
            {rubric.data.criteria.map((c) => (
              <fieldset key={c.key} style={{ border: "none", padding: 0, margin: 0 }}>
                <legend><strong>{c.label}</strong> – <small>{c.question}</small></legend>
                {Object.entries(c.scale).map(([v, desc]) => (
                  <label key={v} className="rubric-opt">
                    <input type="radio" name={c.key} checked={scores[c.key] === Number(v)} onChange={() => setScores({ ...scores, [c.key]: Number(v) })} />
                    <span><strong>{v}</strong> – {desc}</span>
                  </label>
                ))}
              </fieldset>
            ))}
            <label>Kommentar (z. B. wenn die Regel unklar war)<textarea value={comment} onChange={(e) => setComment(e.target.value)} /></label>
            {err && <p className="error">{err}</p>}
            <button className="primary" disabled={!complete} onClick={submit}>Speichern & nächste</button>
          </div>
        </div>
      )}
    </div>
  );
}
