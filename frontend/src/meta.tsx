import { createContext, useContext, type ReactNode } from "react";
import { api } from "./api/client";
import type { Meta } from "./api/types";
import { useAsync } from "./hooks";

const MetaContext = createContext<Meta | null>(null);

export function MetaProvider({ children }: { children: ReactNode }) {
  const { data, error } = useAsync(api.meta);
  if (error) return <main><p className="error">Backend nicht erreichbar: {error}</p><p className="muted">Läuft <code>uvicorn app.main:app</code> auf Port 8000?</p></main>;
  if (!data) return <main><p className="muted">Lade …</p></main>;
  return <MetaContext.Provider value={data}>{children}</MetaContext.Provider>;
}

export function useMeta(): Meta {
  const m = useContext(MetaContext);
  if (!m) throw new Error("MetaProvider missing");
  return m;
}
