import { useEffect, useState } from "react";
import { api, type EvalRequest } from "../../api/client";
import type { EvalRun, EvalRunRow } from "../../api/types";
import { GroupChart } from "../../components/GroupChart";
import { AttributePicker, Loading, Pill, RecPill, Stat } from "../../components/ui";
import { pct, useAsync } from "../../hooks";
import { useMeta } from "../../meta";

export default function ModelTab() {
  const runs = useAsync(api.evalRuns);
  const [selected, setSelected] = useState<string>();
  const running = runs.data?.some((r) => r.status === "running");
  const reloadRuns = runs.reload;

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => void reloadRuns(), 2000);
    return () => clearInterval(t);
  }, [running, reloadRuns]);

  useEffect(() => {
    if (!selected && runs.data) setSelected(runs.data.find((r) => r.status === "done")?.id);
  }, [runs.data, selected]);

  return (
    <div className="stack">
      <div className="grid-2">
        <RunForm onStarted={() => void runs.reload()} />
        <div className="card">
          <h3>Eval-Läufe</h3>
          <Loading error={runs.error} loading={runs.loading && !runs.data} />
          <div className="table-wrap">
            <table>
              <thead><tr><th>Zeit</th><th>Provider</th><th>Blinding</th><th>Judge</th><th>Status</th><th /></tr></thead>
              <tbody>{runs.data?.map((r) => (
                <tr key={r.id} style={{ background: r.id === selected ? "var(--surface-2)" : undefined }}>
                  <td>{new Date(r.created_at).toLocaleString("de-DE")}</td>
                  <td>{r.provider} · <small>{r.model}</small></td>
                  <td>{r.blinding ? "an" : "aus"}</td><td>{r.use_judge ? "ja" : "nein"}</td>
                  <td>{r.status === "running" ? <Pill tone="info">{r.done}/{r.total}</Pill> : r.status === "done" ? <Pill tone="good">fertig</Pill> : <Pill tone="critical" >fehlgeschlagen</Pill>}</td>
                  <td>{r.status === "done" && <button className="chip" onClick={() => setSelected(r.id)}>Anzeigen</button>}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </div>
      <Comparison runs={runs.data?.filter((r) => r.status === "done") ?? []} />
      {selected && <RunView id={selected} />}
    </div>
  );
}

function RunForm({ onStarted }: { onStarted: () => void }) {
  const meta = useMeta();
  const status = useAsync(api.status);
  const questions = useAsync(api.evalQuestions);
  const [req, setReq] = useState<EvalRequest>({ provider: null, blinding: false, use_judge: false, attributes: Object.keys(meta.attributes), question_ids: null, repetitions: 1 });
  const [estimate, setEstimate] = useState<number>();
  const [err, setErr] = useState<string>();

  useEffect(() => { api.evalEstimate(req).then((e) => setEstimate(e.llm_calls)).catch(() => setEstimate(undefined)); }, [req]);

  const toggleAttr = (a: string) => {
    const cur = req.attributes ?? [];
    setReq({ ...req, attributes: cur.includes(a) ? cur.filter((x) => x !== a) : [...cur, a] });
  };
  const qids = req.question_ids ?? questions.data?.questions.map((q) => q.id) ?? [];
  const toggleQ = (id: string) => setReq({ ...req, question_ids: qids.includes(id) ? qids.filter((x) => x !== id) : [...qids, id] });

  async function start() {
    try {
      setErr(undefined);
      await api.startEval(req);
      onStarted();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="card stack">
      <h3>Kontrafaktischen Test starten</h3>
      <small>Jede Frage wird mit der Referenz-Persona und dann mit genau <em>einem</em> geänderten Merkmal gestellt. Der Sachverhalt bleibt gleich.</small>
      <div className="row">
        <label>Provider
          <select value={req.provider ?? ""} onChange={(e) => setReq({ ...req, provider: e.target.value || null })}>
            <option value="">Standard</option>
            {status.data?.providers.map((p) => <option key={p.name} value={p.name}>{p.name} · {p.model}</option>)}
          </select>
        </label>
        <label>Wiederholungen<input type="number" min={1} max={5} value={req.repetitions ?? 1} onChange={(e) => setReq({ ...req, repetitions: Number(e.target.value) })} style={{ width: 70 }} /></label>
      </div>
      <label className="check"><input type="checkbox" checked={!!req.blinding} onChange={(e) => setReq({ ...req, blinding: e.target.checked })} />Blinding an (Gegenmaßnahme testen)</label>
      <label className="check"><input type="checkbox" checked={!!req.use_judge} onChange={(e) => setReq({ ...req, use_judge: e.target.checked })} />LLM-Judge für Antwortqualität (verdoppelt Aufrufe)</label>
      <div>
        <small>Merkmale</small>
        <div className="row">{Object.entries(meta.attributes).map(([a, m]) => (
          <button key={a} className={`chip ${req.attributes?.includes(a) ? "on" : ""}`} onClick={() => toggleAttr(a)}>{m.label}</button>
        ))}</div>
      </div>
      <div>
        <small>Fragen</small>
        <div className="row">{questions.data?.questions.map((q) => (
          <button key={q.id} className={`chip ${qids.includes(q.id) ? "on" : ""}`} onClick={() => toggleQ(q.id)}>{q.id.replace(/_/g, " ")}</button>
        ))}</div>
      </div>
      {err && <p className="error">{err}</p>}
      <button className="primary" onClick={start} disabled={!req.attributes?.length || !qids.length}>
        Starten {estimate !== undefined && `(${estimate} LLM-Aufrufe)`}
      </button>
    </div>
  );
}

function Comparison({ runs }: { runs: EvalRunRow[] }) {
  const meta = useMeta();
  const [details, setDetails] = useState<EvalRun[]>([]);
  const ids = runs.slice(0, 6).map((r) => r.id).join(",");
  useEffect(() => {
    if (!ids) return;
    Promise.all(ids.split(",").map((id) => api.evalRun(id))).then(setDetails).catch(() => undefined);
  }, [ids]);
  if (details.length < 2) return null;
  const attrs = Object.keys(meta.attributes);
  const gapCell = (run: EvalRun, a: string) => {
    const s = run.summary?.attributes.find((x) => x.attribute === a);
    if (!s) return <td key={a} className="num">–</td>;
    return <td key={a} className="num">{pct(s.accuracy_gap.gap)} / {pct(s.favorable_gap.gap)} {s.alert ? "⚠" : ""}</td>;
  };
  return (
    <div className="card">
      <h3>Vergleich der Läufe</h3>
      <small>Je Merkmal: Lücke in der Korrektheit / Lücke in der Quote günstiger Empfehlungen. ⚠ = über dem Schwellwert. Vergleiche z. B. Blinding an und aus oder OpenAI und Groq.</small>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Lauf</th><th className="num">Gesamt</th><th className="num">Schwächste</th>{attrs.map((a) => <th key={a} className="num">{meta.attributes[a].label}</th>)}</tr></thead>
          <tbody>{details.map((r) => (
            <tr key={r.id}>
              <td>{r.provider} · Blinding {r.blinding ? "an" : "aus"}<br /><small>{new Date(r.created_at).toLocaleString("de-DE")}</small></td>
              <td className="num">{pct(r.summary?.overall.accuracy)}</td><td className="num">{pct(r.summary?.worst_group_accuracy)}</td>
              {attrs.map((a) => gapCell(r, a))}
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

function RunView({ id }: { id: string }) {
  const meta = useMeta();
  const run = useAsync(() => api.evalRun(id), [id]);
  const evalSet = useAsync(api.evalQuestions);
  const [attr, setAttr] = useState<string>();
  const s = run.data?.summary;
  useEffect(() => { if (s && (!attr || !s.attributes.some((a) => a.attribute === attr))) setAttr(s.attributes[0]?.attribute); }, [s, attr]);
  if (!s) return <Loading error={run.error} loading={run.loading} />;
  const a = s.attributes.find((x) => x.attribute === attr) ?? s.attributes[0];
  const overallAcc = s.overall.accuracy ?? 0;
  const values = a ? a.groups.map((g) => g.value) : [];
  const refValue = a ? evalSet.data?.reference_persona[a.attribute] : undefined;

  return (
    <div className="stack">
      <h3>Ergebnis: {run.data?.provider} · Blinding {run.data?.blinding ? "an" : "aus"}</h3>
      <div className="tiles">
        <Stat k="Gesamt-Korrektheit" v={pct(s.overall.accuracy)} s={`${s.n} Fälle${s.errors ? `, ${s.errors} Fehler` : ""}`} />
        <Stat k="Schwächste geschützte Gruppe" v={pct(s.worst_group_accuracy)} s="niedrigste Gruppen-Korrektheit" />
        <Stat k="Günstige Empfehlungen" v={pct(s.overall.favorable_rate)} s="Erstattung/Ersatz/Kulanz" />
        <Stat k="Judge-Qualität" v={s.overall.judge_mean?.toFixed(2) ?? "–"} s="1–5, ohne Persona bewertet" />
      </div>
      {s.worst_group_accuracy !== null && overallAcc - s.worst_group_accuracy > s.threshold && (
        <div className="callout crit">Die Gesamtgenauigkeit von {pct(overallAcc)} verbirgt eine Gruppe mit nur {pct(s.worst_group_accuracy)}.</div>
      )}
      {a && (
        <>
          <AttributePicker value={a.attribute} onChange={setAttr} only={s.attributes.map((x) => x.attribute)} />
          <div className="row">
            {a.legitimate ? <Pill tone="info">Legitimes Merkmal: Unterschiede sind laut Policy zulässig</Pill>
              : a.alert ? <Pill tone="critical">Lücke über {pct(s.threshold)}: Bias-Verdacht</Pill> : <Pill tone="good">Lücken unter {pct(s.threshold)}</Pill>}
            <small>Korrektheit: Lücke {pct(a.accuracy_gap.gap)} (schwächste: {a.accuracy_gap.worst ?? "–"}) · Günstige Empfehlungen: Lücke {pct(a.favorable_gap.gap)}</small>
          </div>
          <div className="grid-2">
            <GroupChart title="Policy-Korrektheit" groups={a.groups} series={[{ key: "accuracy", label: "Korrektheit" }]} reference={{ value: overallAcc, label: "Gesamt" }} />
            <GroupChart title="Quote günstiger Empfehlungen" groups={a.groups} series={[{ key: "favorable_rate", label: "günstig" }]} />
            <GroupChart title="Abweichung von Referenz-Persona (Flip-Rate)" groups={a.groups} series={[{ key: "flip_rate", label: "andere Empfehlung als Referenz" }]}
              note="Wie oft ändert sich die Empfehlung, wenn nur dieses Merkmal anders ist?" />
            <GroupChart title="Antwortlänge (Zeichen)" groups={a.groups} series={[{ key: "mean_len", label: "Zeichen" }]} format="num" digits={0} />
          </div>
          <div className="card">
            <h4>Empfehlungen je Frage</h4>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Frage</th><th>erwartet</th>{values.map((v) => <th key={v}>{meta.attributes[a.attribute].values[v] ?? v}</th>)}</tr></thead>
                <tbody>{s.by_question.map((q) => (
                  <tr key={q.question_id}>
                    <td>{q.question_id}</td>
                    <td>{q.expected.map((e) => meta.rec_types[e]).join(" / ")}</td>
                    {values.map((v) => {
                      const cells = q.cells.filter((c) => (c.axis === a.attribute && c.value === v) || (c.axis === "reference" && refValue === v));
                      return <td key={v}>{cells.length ? cells.map((c, i) => <span key={i}>{c.correct ? "✓ " : "✗ "}<RecPill type={c.rec_type} /> </span>) : "–"}</td>;
                    })}
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <small>Die Spalte der Referenz-Persona ({refValue ? meta.attributes[a.attribute].values[refValue] : "–"}) enthält die Referenzläufe.</small>
          </div>
        </>
      )}
    </div>
  );
}
