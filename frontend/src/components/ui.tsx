import type { ReactNode } from "react";
import type { Source } from "../api/client";
import type { PhaseKey } from "../phases";
import { PHASES } from "../phases";
import { useMeta } from "../meta";

export function Stat({ k, v, s }: { k: string; v: ReactNode; s?: ReactNode }) {
  return (
    <div className="stat">
      <div className="k">{k}</div>
      <div className="v">{v}</div>
      {s && <div className="s">{s}</div>}
    </div>
  );
}

export function Pill({ tone = "", children }: { tone?: "" | "good" | "warning" | "serious" | "critical" | "info"; children: ReactNode }) {
  return <span className={`pill ${tone}`}>{children}</span>;
}

export function PhaseIntro({ phase }: { phase: PhaseKey }) {
  const p = PHASES.find((x) => x.key === phase)!;
  return (
    <div className="card">
      <div className="grid-3">
        <div><small>Prüffrage</small><h3 style={{ marginTop: 2 }}>{p.question}</h3></div>
        <div><small>Typisches Beispiel</small><p style={{ marginTop: 2 }}>{p.example}</p></div>
        <div><small>Abfederung in dieser App</small><p style={{ marginTop: 2 }}>{p.mitigation}</p></div>
      </div>
    </div>
  );
}

export function Sources({ sources }: { sources: Source[] }) {
  if (!sources.length) return <small>Keine Quellen gefunden.</small>;
  return (
    <details>
      <summary>Quellen ({sources.length})</summary>
      {sources.map((s) => (
        <div key={s.id} className="source">
          <strong>{s.title}</strong> <small>[{s.id}] · Ähnlichkeit {s.score.toFixed(2)}</small>
          <div>{s.text}</div>
        </div>
      ))}
    </details>
  );
}

export function RecPill({ type }: { type: string }) {
  const meta = useMeta();
  const tone = type === "deny" ? "critical" : type === "escalate" ? "warning" : meta.favorable_types.includes(type as never) ? "good" : "info";
  return <Pill tone={tone}>{meta.rec_types[type as keyof typeof meta.rec_types] ?? type}</Pill>;
}

export function AttributePicker({ value, onChange, only }: { value: string; onChange: (a: string) => void; only?: string[] }) {
  const meta = useMeta();
  const attrs = Object.keys(meta.attributes).filter((a) => !only || only.includes(a));
  return (
    <div className="row" role="group" aria-label="Merkmal wählen">
      <small>Merkmal:</small>
      {attrs.map((a) => (
        <button key={a} className={`chip ${value === a ? "on" : ""}`} onClick={() => onChange(a)} aria-pressed={value === a}>
          {meta.attributes[a].label}
          {meta.legitimate_attributes.includes(a) ? " (legitim)" : ""}
        </button>
      ))}
    </div>
  );
}

export function Loading({ error, loading }: { error?: string; loading?: boolean }) {
  if (error) return <p className="error">{error}</p>;
  if (loading) return <p className="muted">Lade …</p>;
  return null;
}
