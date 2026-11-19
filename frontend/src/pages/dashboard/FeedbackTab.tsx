import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { FeedbackDash } from "../../api/types";
import { GroupChart } from "../../components/GroupChart";
import { AttributePicker, Loading, Pill, Stat } from "../../components/ui";
import { pct, useAsync } from "../../hooks";

export default function FeedbackTab() {
  const d = useAsync(() => api.dashboard<FeedbackDash>("feedback"));
  const [attr, setAttr] = useState("language_style");
  if (!d.data) return <Loading error={d.error} loading />;
  const x = d.data;
  const groups = x.attributes[attr].groups;
  const counts = { pending: 0, approved: 0, rejected: 0 };
  x.suggestions.forEach((s) => counts[s.status]++);

  return (
    <div className="stack">
      <div className="tiles">
        <Stat k="Feedback-Abdeckung" v={pct(x.feedback_coverage)} s={`${x.feedback} von ${x.interactions} Anfragen`} />
        <Stat k="Holdout: Mensch widerspricht" v={pct(x.holdout.human_disagreement_rate)} s={`${x.holdout.decided} entschiedene Holdout-Fälle`} />
        <Stat k="KB-Vorschläge offen" v={counts.pending} s={`${counts.approved} freigegeben · ${counts.rejected} abgelehnt`} />
        <Stat k="Automatisches Lernen" v={x.auto_learning ? "an" : "aus"} s="Änderungen nur nach menschlicher Freigabe" />
      </div>
      <small>{x.holdout.explanation}</small>
      {x.warnings.map((w) => <div key={w} className="callout warn">{w}</div>)}

      <AttributePicker value={attr} onChange={setAttr} />
      <GroupChart title="Repräsentanz im Feedback (1,0 = proportional)" groups={groups} series={[{ key: "representation_ratio", label: "Feedback-Anteil / Verkehrsanteil" }]}
        format="num" domain={[0, 2]} reference={{ value: 1, label: "proportional" }}
        note="Unter 1: Diese Gruppe liefert weniger Feedback, als sie Anfragen stellt. Würde man auf Feedback trainieren, verlöre sie Einfluss." />
      <div className="grid-2">
        <GroupChart title="Hilfreich-Quote" groups={groups} series={[{ key: "helpful_rate", label: "hilfreich" }]} />
        <GroupChart title="Gelöst-Quote" groups={groups} series={[{ key: "resolved_rate", label: "gelöst" }]} />
      </div>

      <div className="card">
        <h3>KB-Vorschläge</h3>
        <small>Freigabe unter <Link to="/settings">Einstellungen</Link>.</small>
        <table>
          <thead><tr><th>Status</th><th>Grund</th><th>Anfrage</th><th>Prüfer:in</th></tr></thead>
          <tbody>{x.suggestions.slice(0, 15).map((s) => (
            <tr key={s.id}>
              <td><Pill tone={s.status === "approved" ? "good" : s.status === "rejected" ? "" : "warning"}>{s.status}</Pill></td>
              <td>{s.reason.replace(/_/g, " ")}</td><td>{s.question.slice(0, 120)}</td><td>{s.reviewer ?? "–"}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
