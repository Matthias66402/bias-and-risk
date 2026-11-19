import { useState } from "react";
import { api } from "../../api/client";
import type { DeploymentDash } from "../../api/types";
import { GroupChart } from "../../components/GroupChart";
import { AttributePicker, Loading, Stat } from "../../components/ui";
import { num, pct, useAsync } from "../../hooks";

export default function DeploymentTab() {
  const d = useAsync(() => api.dashboard<DeploymentDash>("deployment"));
  const [attr, setAttr] = useState("name_origin");
  if (!d.data) return <Loading error={d.error} loading />;
  const x = d.data;
  const reasons = x.route_reasons.map((r) => ({ value: r.reason, label: r.label, n: r.n, share: x.interactions ? r.n / x.interactions : 0 }));
  const groups = x.by_group[attr].groups;

  return (
    <div className="stack">
      <div className="tiles">
        <Stat k="Automatisch beantwortet" v={pct(x.auto_rate)} s={`${x.interactions} Chat-Anfragen`} />
        <Stat k="Offen in der Queue" v={x.queue_pending} s={`${x.decided} entschieden`} />
        <Stat k="Überstimmt" v={pct(x.override_rate)} s="Mensch entschied anders als Modell" />
        <Stat k="Durchgewinkt" v={pct(x.rubber_stamp_rate)} s={`übernommen in < ${x.rubber_stamp_seconds} s`} />
        <Stat k="Ø Prüfzeit" v={x.mean_review_seconds === null ? "–" : `${num(x.mean_review_seconds, 0)} s`} />
        <Stat k="Abgelehnte Empfehlungen revidiert" v={pct(x.negative_overridden_rate)} s="Ablehnung → anderes Ergebnis" />
      </div>
      {x.rubber_stamp_rate !== null && x.rubber_stamp_rate > 0.5 && (
        <div className="callout crit">Mehr als die Hälfte der Entscheidungen wurde ohne echte Prüfung übernommen. Die Empfehlung wird faktisch zur automatischen Entscheidung (Automation Bias).</div>
      )}
      <GroupChart title="Warum ging ein Fall an einen Menschen?" groups={reasons} series={[{ key: "share", label: "Anteil" }]} />

      <h3>Nach Gruppe</h3>
      <AttributePicker value={attr} onChange={setAttr} />
      <div className="grid-2">
        <GroupChart title="Anteil an Menschen weitergeleitet" groups={groups} series={[{ key: "routed_rate", label: "weitergeleitet" }]} />
        <GroupChart title="Überstimmungsquote" groups={groups} series={[{ key: "override_rate", label: "überstimmt" }]} />
      </div>
      <GroupChart title="Günstiges Ergebnis: Modell vs. Mensch" groups={groups}
        series={[{ key: "model_favorable_rate", label: "Modell-Empfehlung" }, { key: "human_favorable_rate", label: "Entscheidung Mensch" }]}
        note="Auch menschliche Entscheidungen können verzerrt sein. Deshalb sehen Prüfer:innen weder Namen noch geschützte Merkmale." />
    </div>
  );
}
