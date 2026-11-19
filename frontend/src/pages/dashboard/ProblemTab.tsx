import { useState } from "react";
import { api } from "../../api/client";
import type { ProblemDash } from "../../api/types";
import { GroupChart } from "../../components/GroupChart";
import { AttributePicker, Loading, Pill, Stat } from "../../components/ui";
import { pct, useAsync } from "../../hooks";

export default function ProblemTab() {
  const d = useAsync(() => api.dashboard<ProblemDash>("problem"));
  const [attr, setAttr] = useState("name_origin");
  if (!d.data) return <Loading error={d.error} loading />;
  const { config, overall } = d.data;

  return (
    <div className="stack">
      <div className="card">
        <h3>Zweck</h3>
        <p>{config.purpose}</p>
        <div className="grid-2">
          <div>
            <h4>Entscheidungen dürfen sich stützen auf</h4>
            <ul>{config.decision_sources.allowed.map((s) => <li key={s}>{s}</li>)}</ul>
          </div>
          <div>
            <h4>Bewusst ausgeschlossen</h4>
            <ul>{config.decision_sources.excluded.map((s) => <li key={s}>{s}</li>)}</ul>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="stack">
          <h3>Eigentliches Ziel</h3>
          <div className="tiles">
            <Stat k="Lösungsrate (Feedback)" v={pct(overall.resolution_rate)} s="Anteil „gelöst“ an Feedback mit Angabe" />
            <Stat k="Policy-Korrektheit (Eval)" v={pct(overall.policy_accuracy)} s="letzter Eval-Lauf" />
            <Stat k="Schwächste Gruppe (Eval)" v={pct(overall.worst_group_accuracy)} s="geschützte Merkmale" />
          </div>
        </div>
        <div className="stack">
          <h3>Proxy-Metriken (nicht optimiert)</h3>
          <div className="tiles">
            <Stat k="Deflection-Rate" v={pct(overall.deflection_rate)} s="ohne Mensch abgeschlossen" />
            <Stat k="Proxy-Warnungen" v={d.data.proxy_warnings.count} s="Begründungen mit Proxy-Begriffen" />
            <Stat k="Anfragen mit Blinding" v={pct(overall.blinding_share)} />
          </div>
          {config.proxy_metrics.map((m) => <div key={m.key} className="callout warn"><strong>{m.label}:</strong> {m.warning}</div>)}
        </div>
      </div>

      <AttributePicker value={attr} onChange={setAttr} />
      <GroupChart
        title={`Proxy vs. Ziel nach ${d.data.by_group[attr].label}`}
        groups={d.data.by_group[attr].groups}
        series={[{ key: "deflection_rate", label: "Deflection (Proxy)" }, { key: "resolution_rate", label: "Lösungsrate (Ziel)" }]}
        note="Hohe Deflection bei niedriger Lösungsrate heißt: Die Gruppe wird abgewimmelt statt geholfen."
      />

      <div className="card">
        <h3>Letzte Proxy-Warnungen</h3>
        {d.data.proxy_warnings.recent.length === 0 ? <p className="muted">Keine. Begründungen nannten bisher keine Proxy-Merkmale.</p> : (
          <table>
            <thead><tr><th>Begriffe</th><th>Begründung</th></tr></thead>
            <tbody>{d.data.proxy_warnings.recent.map((w) => (
              <tr key={w.interaction_id}><td>{w.terms.map((t) => <Pill key={t} tone="critical">{t}</Pill>)}</td><td>{w.rationale}</td></tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}
