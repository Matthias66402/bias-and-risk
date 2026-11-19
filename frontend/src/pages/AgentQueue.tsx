import { useEffect, useRef, useState } from "react";
import { api, type RecType } from "../api/client";
import type { QueueItem } from "../api/types";
import { Loading, Pill, RecPill, Sources } from "../components/ui";
import { useAsync, useStoredString } from "../hooks";
import { useMeta } from "../meta";

export default function AgentQueue() {
  const [tab, setTab] = useState<"pending" | "decided">("pending");
  const list = useAsync(() => api.queue(tab), [tab]);
  const [selected, setSelected] = useState<QueueItem | null>(null);

  useEffect(() => { setSelected(null); }, [tab]);

  return (
    <div className="stack">
      <div className="callout">
        <strong>Phase 5 – Einsatz:</strong> Hier landen Ablehnungen, unsichere Fälle, Proxy-Verdachtsfälle und eine Zufallsstichprobe (Holdout).
        Du siehst den Text ohne Namen und nur legitime Merkmale. Deine Entscheidung braucht eine eigene Begründung. Schnelles, unverändertes Übernehmen zählt als „Durchwinken“.
      </div>
      <div className="tabs">
        <button className={tab === "pending" ? "on" : ""} onClick={() => setTab("pending")}>Offen</button>
        <button className={tab === "decided" ? "on" : ""} onClick={() => setTab("decided")}>Entschieden</button>
      </div>
      <Loading error={list.error} loading={list.loading && !list.data} />
      <div className="split">
        <div className="stack">
          {list.data?.length === 0 && <p className="muted">Keine Einträge.</p>}
          {list.data?.map((q) => (
            <button key={q.queue_id} onClick={() => setSelected(q)} className="card" style={{ textAlign: "left", outline: selected?.queue_id === q.queue_id ? "2px solid var(--accent)" : undefined }}>
              <div className="row"><strong>#{q.queue_id}</strong><Pill tone={q.is_holdout ? "info" : "warning"}>{q.route_reason.replace(/_/g, " ")}</Pill><small>{new Date(q.created_at).toLocaleString("de-DE")}</small></div>
              <div style={{ marginTop: 4 }}>{q.message.slice(0, 110)}{q.message.length > 110 ? " …" : ""}</div>
            </button>
          ))}
        </div>
        {selected && <Review key={selected.queue_id} item={selected} onDone={() => { setSelected(null); void list.reload(); }} />}
      </div>
    </div>
  );
}

function Review({ item, onDone }: { item: QueueItem; onDone: () => void }) {
  const meta = useMeta();
  const opened = useRef(Date.now());
  const [blindReview, setBlindReview] = useState(true);
  const [revealed, setRevealed] = useState(false);
  const [finalType, setFinalType] = useState<RecType | "">("");
  const [rationale, setRationale] = useState("");
  const [reviewer, setReviewer] = useStoredString("reviewer", "");
  const [err, setErr] = useState<string>();
  const showRec = !blindReview || revealed || item.status === "decided";

  async function submit() {
    if (!finalType) return;
    try {
      await api.decide(item.queue_id, { final_type: finalType, rationale, reviewer, review_seconds: (Date.now() - opened.current) / 1000 });
      onDone();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="card stack">
      <div>
        <h3>Anfrage <small className="muted">#{item.queue_id}</small></h3>
        <div className="pre">{item.message}</div>
        <small>Sichtbare Merkmale: {Object.entries(item.visible_attributes).map(([k, v]) => `${meta.attributes[k]?.label}: ${meta.attributes[k]?.values[v] ?? v}`).join(" · ") || "–"}</small>
      </div>
      <Sources sources={item.sources} />

      {item.status === "pending" && (
        <label className="check">
          <input type="checkbox" checked={blindReview} onChange={(e) => setBlindReview(e.target.checked)} />
          Blind-Review: Empfehlung erst nach eigener Einschätzung anzeigen (gegen Ankereffekt)
        </label>
      )}

      {showRec ? (
        <div className="rec">
          <h4>Empfehlung des Modells – du entscheidest</h4>
          <div className="row"><RecPill type={item.recommendation.type} /><small>Konfidenz {(item.recommendation.confidence * 100).toFixed(0)} %</small></div>
          <p style={{ margin: "0.4rem 0" }}><small>Begründung: {item.recommendation.rationale}</small></p>
          {item.proxy_warnings.length > 0 && <div className="callout crit">Proxy-Verdacht: {item.proxy_warnings.join(", ")}</div>}
          <details><summary>Entwurf der Kundenantwort</summary><div className="source">{item.answer}</div></details>
        </div>
      ) : (
        <button onClick={() => setRevealed(true)} disabled={!finalType}>
          {finalType ? "Empfehlung des Modells anzeigen" : "Erst eigene Einschätzung wählen, dann Empfehlung anzeigen"}
        </button>
      )}

      {item.status === "decided" && item.decision ? (
        <div className="callout">
          Entscheidung: <RecPill type={item.decision.final_type} /> {item.decision.accepted ? "(Empfehlung übernommen)" : "(überstimmt)"} – {item.decision.reviewer},
          {" "}{item.decision.review_seconds.toFixed(0)} s<br /><small>{item.decision.rationale}</small>
        </div>
      ) : (
        <div className="stack">
          <label>
            Deine Entscheidung
            <select value={finalType} onChange={(e) => setFinalType(e.target.value as RecType)}>
              <option value="">– bitte wählen –</option>
              {Object.entries(meta.rec_types).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label>
            Eigene Begründung (Pflicht, min. 10 Zeichen)
            <textarea value={rationale} onChange={(e) => setRationale(e.target.value)} placeholder="Welche Policy-Regel trifft zu und warum?" />
          </label>
          <label>Dein Name<input value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label>
          {err && <p className="error">{err}</p>}
          <button className="primary" disabled={!finalType || rationale.trim().length < 10 || !reviewer.trim() || !showRec} onClick={submit}>
            Entscheidung speichern
          </button>
          {!showRec && <small>Vor dem Speichern bitte die Empfehlung ansehen, damit Abweichungen bewusst passieren.</small>}
        </div>
      )}
    </div>
  );
}
