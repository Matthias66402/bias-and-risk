import { useState } from "react";
import { api } from "../../api/client";
import type { DataDash } from "../../api/types";
import { GroupChart } from "../../components/GroupChart";
import { AttributePicker, Loading, Pill } from "../../components/ui";
import { useAsync } from "../../hooks";
import { useMeta } from "../../meta";

export default function DataTab() {
  const meta = useMeta();
  const d = useAsync(() => api.dashboard<DataDash>("data"));
  const [attr, setAttr] = useState("language_style");
  if (!d.data) return <Loading error={d.error} loading />;
  const { kb, eval_set, live } = d.data;
  const styleLabel = (s: string) => meta.attributes.language_style.values[s] ?? s;
  const groups = live.attributes[attr].groups;

  return (
    <div className="stack">
      <div className="grid-2">
        <div className="card">
          <h3>Wissensbasis: Thema × Sprachstil</h3>
          <small>Anzahl passender KB-Abschnitte ({kb.chunks} gesamt). Rote Zellen = für diese Gruppe gibt es kein passendes Material.</small>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Thema</th>{kb.styles.map((s) => <th key={s} className="num">{styleLabel(s)}</th>)}</tr></thead>
              <tbody>{kb.matrix.map((r) => (
                <tr key={r.topic}><td>{r.topic}</td>{kb.styles.map((s) => <td key={s} className={`num ${r[s] === 0 ? "gap" : ""}`}>{r[s] === 0 ? "✗ 0" : r[s]}</td>)}</tr>
              ))}</tbody>
            </table>
          </div>
          <p style={{ marginTop: 8 }}><Pill tone={kb.gaps.length ? "serious" : "good"}>{kb.gaps.length} Lücken</Pill></p>
        </div>
        <div className="card">
          <h3>Eval-Set: Frage × Sprachstil</h3>
          <small>Werden alle Gruppen überhaupt getestet?</small>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Frage</th><th>Thema</th>{eval_set.styles.map((s) => <th key={s} className="num">{styleLabel(s)}</th>)}</tr></thead>
              <tbody>{eval_set.rows.map((r) => (
                <tr key={r.question}><td>{r.question}</td><td>{r.topic}</td>{eval_set.styles.map((s) => <td key={s} className={`num ${r[s] ? "" : "gap"}`}>{r[s] ? "✓" : "✗"}</td>)}</tr>
              ))}</tbody>
            </table>
          </div>
          <small>Nicht getestete KB-Themen: {kb.matrix.map((r) => r.topic).filter((t) => !eval_set.topics.includes(t)).join(", ") || "keine"}</small>
        </div>
      </div>

      <h3>Live-Verkehr ({live.total} Chat-Anfragen)</h3>
      <AttributePicker value={attr} onChange={setAttr} />
      {groups.some((g) => g.underrepresented) && (
        <div className="callout warn">Unterrepräsentiert: {groups.filter((g) => g.underrepresented).map((g) => g.label).join(", ")}. Aussagen über diese Gruppen sind unsicher.</div>
      )}
      {groups.some((g) => g.retrieval_gap) && (
        <div className="callout crit">Deutlich mehr KB-Lücken bei: {groups.filter((g) => g.retrieval_gap).map((g) => g.label).join(", ")}</div>
      )}
      <div className="grid-2">
        <GroupChart title="Anteil am Verkehr" groups={groups} series={[{ key: "share", label: "Anteil" }]} />
        <GroupChart title="Anfragen mit KB-Lücke" groups={groups} series={[{ key: "low_retrieval_rate", label: "KB-Lücke" }]} />
        <GroupChart title="Mittlere Retrieval-Ähnlichkeit" groups={groups} series={[{ key: "mean_top_score", label: "Ähnlichkeit" }]} format="num" domain={[0, 1]} />
        <GroupChart title="Eskalationsquote" groups={groups} series={[{ key: "escalate_rate", label: "Eskalation" }]} />
      </div>
    </div>
  );
}
