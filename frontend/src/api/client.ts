import type { components } from "./schema";

type S = components["schemas"];
export type Persona = S["Persona"];
export type ChatRequest = S["ChatRequest"];
export type ChatResponse = S["ChatResponse"];
export type Source = S["Source"];
export type RuntimeSettings = S["RuntimeSettings"];
export type DecisionIn = S["DecisionIn"];
export type LabelIn = S["LabelIn"];
export type EvalRequest = S["EvalRequest"];
export type FeedbackIn = S["FeedbackIn"];
export type SuggestionDecisionIn = S["SuggestionDecisionIn"];
export type RecType = S["Recommendation"]["type"];

export class ApiError extends Error {}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* keep status text */
    }
    throw new ApiError(detail);
  }
  return res.json() as Promise<T>;
}

const q = (params: Record<string, string | undefined>) => {
  const s = new URLSearchParams(Object.entries(params).filter((e): e is [string, string] => e[1] !== undefined));
  return s.toString() ? `?${s}` : "";
};

export const api = {
  meta: () => req<import("./types").Meta>("GET", "/meta"),
  chat: (b: ChatRequest) => req<ChatResponse>("POST", "/chat", b),
  feedback: (b: FeedbackIn) => req<{ feedback_id: number; suggestion_id: number | null }>("POST", "/feedback", b),

  queue: (status: "pending" | "decided") => req<import("./types").QueueItem[]>("GET", `/queue${q({ status })}`),
  decide: (id: number, b: DecisionIn) => req<{ accepted: boolean }>("POST", `/queue/${id}/decision`, b),

  rubric: () => req<import("./types").Rubric>("GET", "/labeling/rubric"),
  nextLabel: (annotator: string) => req<import("./types").LabelItem | null>("GET", `/labeling/next${q({ annotator })}`),
  submitLabel: (b: LabelIn) => req<{ ok: boolean }>("POST", "/labeling", b),

  evalQuestions: () => req<import("./types").EvalSet>("GET", "/eval/questions"),
  evalEstimate: (b: EvalRequest) => req<{ cases: number; llm_calls: number }>("POST", "/eval/estimate", b),
  startEval: (b: EvalRequest) => req<{ run_id: string; total: number }>("POST", "/eval/counterfactual", b),
  evalRuns: () => req<import("./types").EvalRunRow[]>("GET", "/eval/runs"),
  evalRun: (id: string) => req<import("./types").EvalRun>("GET", `/eval/runs/${id}`),

  dashboard: <T,>(phase: string) => req<T>("GET", `/dashboard/${phase}`),

  settings: () => req<RuntimeSettings>("GET", "/settings"),
  saveSettings: (b: RuntimeSettings) => req<RuntimeSettings>("PUT", "/settings", b),
  status: () => req<{ chunks: number; embedder: string; providers: { name: string; model: string }[] }>("GET", "/admin/status"),
  ingest: () => req<{ chunks: number; embedder: string }>("POST", "/admin/ingest"),
  suggestions: (status?: string) => req<import("./types").Suggestion[]>("GET", `/kb-suggestions${q({ status })}`),
  decideSuggestion: (id: number, b: SuggestionDecisionIn) => req<{ status: string }>("POST", `/kb-suggestions/${id}/decision`, b),
};
