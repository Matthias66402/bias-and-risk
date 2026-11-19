import { useEffect, useRef, useState } from "react";
import { api, type ChatResponse, type Persona } from "../api/client";
import { Pill, RecPill, Sources } from "../components/ui";
import { useAsync } from "../hooks";
import { useMeta } from "../meta";

type Entry =
  | { kind: "user"; text: string; persona: Persona; blinding: boolean }
  | { kind: "bot"; resp: ChatResponse; question: string; persona: Persona; label?: string; feedback?: "up" | "down" }
  | { kind: "error"; text: string };

const DEFAULT_PERSONA: Required<Persona> = {
  name: "Max Müller", name_origin: "deutsch", language_style: "standard", segment: "stamm", age_group: "30-49", region: "stadt",
};

export default function Chat() {
  const meta = useMeta();
  const [persona, setPersona] = useState<Required<Persona>>(DEFAULT_PERSONA);
  const [blinding, setBlinding] = useState(true);
  const [provider, setProvider] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [entries, setEntries] = useState<Entry[]>([]);
  const status = useAsync(api.status);
  const settings = useAsync(api.settings);
  const examples = useAsync(api.evalQuestions);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (settings.data && !provider) setProvider(settings.data.default_provider ?? ""); }, [settings.data, provider]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [entries]);

  const setAttr = (k: keyof Persona, v: string) => {
    const next = { ...persona, [k]: v };
    if (k === "name_origin" && meta.names_by_origin[v]) next.name = meta.names_by_origin[v];
    setPersona(next);
  };

  async function send(message: string, p: Persona, blind: boolean, label?: string) {
    setBusy(true);
    if (!label) setEntries((e) => [...e, { kind: "user", text: message, persona: p, blinding: blind }]);
    try {
      const resp = await api.chat({ message, persona: p, blinding: blind, provider: provider || null });
      setEntries((e) => [...e, { kind: "bot", resp, question: message, persona: p, label }]);
    } catch (err) {
      setEntries((e) => [...e, { kind: "error", text: err instanceof Error ? err.message : String(err) }]);
    } finally {
      setBusy(false);
    }
  }

  async function giveFeedback(idx: number, helpful: boolean, resolved: boolean) {
    const entry = entries[idx];
    if (entry.kind !== "bot") return;
    await api.feedback({ interaction_id: entry.resp.interaction_id, helpful, resolved });
    setEntries((e) => e.map((x, i) => (i === idx && x.kind === "bot" ? { ...x, feedback: helpful ? "up" : "down" } : x)));
  }

  const select = (k: keyof Persona, label: string) => (
    <label key={k}>
      {label}
      <select value={persona[k]} onChange={(e) => setAttr(k, e.target.value)}>
        {Object.entries(meta.attributes[k].values).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );

  return (
    <div className="split">
      <aside className="card stack">
        <div>
          <h3>Simulierte Persona</h3>
          <small>Die Merkmale dienen dem Monitoring. Mit aktivem Blinding sieht das Modell nur legitime Merkmale (Kundensegment), und der Name wird aus dem Text entfernt.</small>
        </div>
        <label>Name<input value={persona.name} onChange={(e) => setAttr("name", e.target.value)} /></label>
        {select("name_origin", meta.attributes.name_origin.label)}
        {select("language_style", `${meta.attributes.language_style.label} (für Auswertung)`)}
        {select("segment", meta.attributes.segment.label)}
        {select("age_group", meta.attributes.age_group.label)}
        {select("region", meta.attributes.region.label)}
        <label className="check">
          <input type="checkbox" checked={blinding} onChange={(e) => setBlinding(e.target.checked)} />
          Blinding geschützter Merkmale
        </label>
        <label>
          LLM-Provider
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            {status.data?.providers.map((p) => <option key={p.name} value={p.name}>{p.name} · {p.model}</option>)}
          </select>
        </label>
        {examples.data && (
          <div>
            <small>Beispielanfragen im gewählten Sprachstil:</small>
            <div className="row" style={{ marginTop: 4 }}>
              {examples.data.questions.map((q) => (
                <button key={q.id} className="chip" onClick={() => setText(`${q.texts[persona.language_style] ?? q.texts.standard}\n\nViele Grüße\n${persona.name}`)}>
                  {q.id.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </div>
        )}
      </aside>

      <section className="stack">
        <div className="chat">
          {entries.length === 0 && (
            <div className="callout">
              Stelle eine Frage an den Support (z. B. zu Retouren, Lieferung oder Erstattung). Unter jeder Antwort siehst du die <strong>Empfehlung</strong>, ob ein Mensch entscheidet, und was das Modell tatsächlich gesehen hat.
              Mit <em>Gegenprobe</em> wird dieselbe Frage mit umgekehrtem Blinding gestellt.
            </div>
          )}
          {entries.map((e, i) =>
            e.kind === "user" ? (
              <div key={i} className="msg user">{e.text}</div>
            ) : e.kind === "error" ? (
              <div key={i} className="msg bot callout crit">Fehler: {e.text}</div>
            ) : (
              <BotMessage key={i} entry={e} onFeedback={(h, r) => giveFeedback(i, h, r)}
                onCounterCheck={() => send(e.question, e.persona, !e.resp.blinding, `Gegenprobe: Blinding ${e.resp.blinding ? "aus" : "an"}`)} busy={busy} />
            ),
          )}
          <div ref={endRef} />
        </div>
        <form className="composer" onSubmit={(ev) => { ev.preventDefault(); if (text.trim()) { void send(text, persona, blinding); setText(""); } }}>
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Deine Nachricht an den Support …"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} />
          <button className="primary" disabled={busy || !text.trim()}>{busy ? "…" : "Senden"}</button>
        </form>
      </section>
    </div>
  );
}

function BotMessage({ entry, onFeedback, onCounterCheck, busy }: {
  entry: Extract<Entry, { kind: "bot" }>; onFeedback: (helpful: boolean, resolved: boolean) => void; onCounterCheck: () => void; busy: boolean;
}) {
  const meta = useMeta();
  const r = entry.resp;
  return (
    <div className="msg bot card">
      {entry.label && <div style={{ marginBottom: 6 }}><Pill tone="info">{entry.label}</Pill></div>}
      <div className="pre">{r.answer}</div>
      <div className="rec">
        <h4>Empfehlung an Mitarbeiter:in – keine Entscheidung</h4>
        <div className="row">
          <RecPill type={r.recommendation.type} />
          <small>Konfidenz {(r.recommendation.confidence * 100).toFixed(0)} %</small>
          {r.routed_to_human
            ? <Pill tone="warning">Mensch entscheidet: {meta.route_reasons[r.route_reason] ?? r.route_reason}</Pill>
            : <Pill tone="good">Automatisch beantwortet</Pill>}
          {r.low_retrieval && <Pill tone="serious">KB-Lücke (Ähnlichkeit {r.top_score.toFixed(2)})</Pill>}
        </div>
        <p style={{ margin: "0.4rem 0 0" }}><small>Begründung: {r.recommendation.rationale || "–"}</small></p>
        {r.proxy_warnings.length > 0 && (
          <div className="callout crit" style={{ marginTop: 6 }}>Proxy-Verdacht: Die Begründung nennt <strong>{r.proxy_warnings.join(", ")}</strong>.</div>
        )}
      </div>
      <div style={{ marginTop: 6 }}><Sources sources={r.sources} /></div>
      <details>
        <summary>Was hat das Modell gesehen? (Blinding {r.blinding ? "an" : "aus"})</summary>
        <div className="source">
          <strong>Profil:</strong> {Object.keys(r.profile_sent).length ? Object.entries(r.profile_sent).map(([k, v]) => `${k}: ${String(v)}`).join(" · ") : "–"}
          <br /><strong>Nachricht:</strong> {r.message_sent}
        </div>
      </details>
      <div className="row" style={{ marginTop: 8 }}>
        {entry.feedback ? (
          <small>Danke für dein Feedback ({entry.feedback === "up" ? "hilfreich" : "nicht hilfreich – als KB-Vorschlag gemeldet"}).</small>
        ) : (
          <>
            <small>War das hilfreich?</small>
            <button className="chip" onClick={() => onFeedback(true, true)}>👍 Ja, gelöst</button>
            <button className="chip" onClick={() => onFeedback(true, false)}>Hilfreich, aber nicht gelöst</button>
            <button className="chip" onClick={() => onFeedback(false, false)}>👎 Nein</button>
          </>
        )}
        {!entry.label && <button className="chip" disabled={busy} onClick={onCounterCheck} style={{ marginLeft: "auto" }}>Gegenprobe (Blinding {r.blinding ? "aus" : "an"})</button>}
      </div>
      <div className="meta">{r.provider} · {r.model}</div>
    </div>
  );
}
