import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Group } from "../api/types";
import { num, pct } from "../hooks";

export interface Series {
  key: string;
  label: string;
}

interface Props {
  title: string;
  groups: Group[];
  series: Series[];
  format?: "pct" | "num";
  domain?: [number, number];
  reference?: { value: number; label: string };
  note?: string;
  digits?: number;
}

const COLORS = ["var(--series-1)", "var(--series-2)"];

/** Horizontal bars, one row per group. Single series -> no legend; 2 series -> legend. Always has a table view. */
export function GroupChart({ title, groups, series, format = "pct", domain, reference, note, digits = 2 }: Props) {
  const [asTable, setAsTable] = useState(false);
  const fmt = (v: unknown) => (typeof v === "number" ? (format === "pct" ? pct(v) : num(v, digits)) : "–");
  const data = groups.map((g) => ({ ...g, name: `${g.label} (n=${g.n})` }));
  const height = 36 + groups.length * (series.length * 14 + 16);
  const dom = domain ?? (format === "pct" ? [0, 1] : [0, "auto"]);

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
        <h4 style={{ margin: 0 }}>{title}</h4>
        <button className="chip" onClick={() => setAsTable(!asTable)} aria-pressed={asTable}>
          {asTable ? "Diagramm" : "Tabelle"}
        </button>
      </div>
      {series.length > 1 && (
        <div className="chart-legend" style={{ marginBottom: 4 }}>
          {series.map((s, i) => (
            <span key={s.key}><i style={{ background: COLORS[i] }} />{s.label}</span>
          ))}
        </div>
      )}
      {asTable ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Gruppe</th><th className="num">n</th>{series.map((s) => <th key={s.key} className="num">{s.label}</th>)}</tr>
            </thead>
            <tbody>
              {groups.map((g) => (
                <tr key={g.value}><td>{g.label}</td><td className="num">{g.n}</td>{series.map((s) => <td key={s.key} className="num">{fmt(g[s.key])}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 4 }} barGap={2} barCategoryGap={8}>
            <CartesianGrid horizontal={false} stroke="var(--grid)" />
            <XAxis type="number" domain={dom as [number, number]} tickFormatter={(v) => fmt(v)} stroke="var(--axis)" tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
            <YAxis type="category" dataKey="name" width={150} stroke="var(--axis)" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} />
            <Tooltip
              cursor={{ fill: "var(--surface-2)" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const g = payload[0].payload as Group;
                return (
                  <div className="tooltip">
                    <strong>{g.label}</strong> <span className="muted">n={g.n}</span>
                    {series.map((s) => <div key={s.key}>{s.label}: {g.n ? fmt(g[s.key]) : "keine Daten"}</div>)}
                  </div>
                );
              }}
            />
            {reference && (
              <ReferenceLine x={reference.value} stroke="var(--text-muted)" strokeDasharray="4 3"
                label={{ value: reference.label, position: "top", fill: "var(--text-muted)", fontSize: 11 }} />
            )}
            {series.map((s, i) => (
              <Bar key={s.key} dataKey={s.key} name={s.label} fill={COLORS[i]} barSize={12} radius={[0, 4, 4, 0]} isAnimationActive={false} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      )}
      {note && <small>{note}</small>}
    </div>
  );
}
