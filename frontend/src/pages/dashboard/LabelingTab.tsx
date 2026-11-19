import { useState } from "react";
import { api } from "../../api/client";
import type { LabelingDash } from "../../api/types";
import { GroupChart } from "../../components/GroupChart";
import { AttributePicker, Loading, Pill, Stat } from "../../components/ui";
import { num, pct, useAsync } from "../../hooks";
import { useMeta } from "../../meta";

const alphaTone = (a: number | null) => (a === null ? "" : a >= 0.8 ? "good" : a >= 0.667 ? "warning" : "critical");
const alphaText = (a: number | null) => (a === null ? "zu wenig Daten" : a >= 0.8 ? "verlässlich" : a >= 0.667 ? "vorläufig" : "Regel unklar");

export default function LabelingTab() {
  const meta = useMeta();
  const d =useAsync(() => api.dashboard<LabelingDash>("labeling"));
  const [attr, setAttr] = useState("language_style");
  const [crit, setCrit] = useState("korrektheit");
  if (!d.data) return <Loading error={d.error} loading />;
  const x = d.data;
  const label = (k: string) => x.rubric.criteria.find((c) => c.key === k)?.label ?? k;

  return (
    <div className="stack">
      <div className="tiles">
        <Stat k="Labels" v={x.n_labels} s={`Rubrik ${x.rubric.version}`} />
        <Stat k="Bewertete Antworten" v={x.n_items} />
        <Stat k="Mehrfach bewertet" v={x.n_items_multi} s="Grundlage für Übereinstimmung" />
        <Stat k="Annotator:innen" v={x.annotators.length} s={x.annotators.join(", ") || "–"} />
      </div>

      <div className="card">
        <h3>Übereinstimmung je Kriterium</h3>
        <small>Krippendorffs α (nominal): ≥ 0,8 verlässlich, 0,667–0,8 vorläufig, darunter ist die Regel zu unklar. Paarweise Werte sind Cohens κ.</small>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Kriterium</th><th className="num">Items</th><th className="num">volle Einigkeit</th><th className="num">α</th><th>Bewertung</th><th>Paare (κ)</th></tr></thead>
            <tbody>{x.per_criterion.map((c) => (
              <tr key={c.criterion}>
                <td>{label(c.criterion)}</td><td className="num">{c.n_items}</td><td className="num">{pct(c.percent_agreement)}</td>
                <td className="num">{num(c.alpha)}</td><td><Pill tone={alphaTone(c.alpha)}>{alphaText(c.alpha)}</Pill></td>
                <td>{c.pairwise.map((p) => `${p.a}↔${p.b}: ${num(p.kappa)} (n=${p.n})`).join(" · ") || "–"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3>Strenge je Annotator:in</h3>
          <small>Mittlere Punktzahl. Große Unterschiede zeigen, dass das Label davon abhängt, wer bewertet.</small>
          <table>
            <thead><tr><th>Person</th><th className="num">n</th>{x.rubric.criteria.map((c) => <th key={c.key} className="num">{c.label}</th>)}</tr></thead>
            <tbody>{x.leniency.map((l) => (
              <tr key={l.annotator}><td>{l.annotator}</td><td className="num">{l.n}</td>{x.rubric.criteria.map((c) => <td key={c.key} className="num">{num(l[c.key] as number | null)}</td>)}</tr>
            ))}</tbody>
          </table>
        </div>
        <div className="card">
          <h3>Klärungsliste ({x.disagreements.length})</h3>
          <small>Fälle mit starker Uneinigkeit. Sie sind Anlass, die Rubrik zu präzisieren (neue Version).</small>
          {x.disagreements.slice(0, 8).map((dg) => (
            <div key={dg.interaction_id} className="source">
              <div>{dg.message}</div>
              <small>{Object.entries(dg.scores).map(([a, s]) => `${a}: ${Object.values(s).join("/")}`).join(" · ")}</small>
            </div>
          ))}
        </div>
      </div>

      <h3>Labels nach Gruppe (blind vergeben)</h3>
      <div className="row">
        <AttributePicker value={attr} onChange={setAttr} />
        <select value={crit} onChange={(e) => setCrit(e.target.value)}>
          {x.rubric.criteria.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </select>
      </div>
      <GroupChart title={`${label(crit)} nach ${meta.attributes[attr].label}`} groups={x.by_group[attr]} series={[{ key: crit, label: label(crit) }]} format="num" domain={[1, 3]}
        note="Da Annotator:innen die Persona nicht sehen, zeigen Unterschiede echte Qualitätsunterschiede der Antworten." />
    </div>
  );
}
