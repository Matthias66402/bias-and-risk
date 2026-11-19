// Hand-written types for endpoints that return free-form dicts (dashboards etc.).
// Request/response models with Pydantic schemas come from the generated ./schema.d.ts.
import type { RecType, Source } from "./client";

export interface Meta {
  attributes: Record<string, { label: string; values: Record<string, string> }>;
  rec_types: Record<RecType, string>;
  favorable_types: RecType[];
  route_reasons: Record<string, string>;
  protected_attributes: string[];
  legitimate_attributes: string[];
  names_by_origin: Record<string, string>;
}

export interface Rec {
  type: RecType;
  confidence: number;
  rationale: string;
}

export interface QueueItem {
  queue_id: number;
  interaction_id: string;
  status: "pending" | "decided";
  created_at: string;
  route_reason: string;
  is_holdout: boolean;
  message: string;
  visible_attributes: Record<string, string>;
  answer: string;
  recommendation: Rec;
  sources: Source[];
  proxy_warnings: string[];
  decision: null | { final_type: RecType; accepted: boolean; rationale: string; reviewer: string; review_seconds: number; decided_at: string };
}

export interface RubricCriterion {
  key: string;
  label: string;
  question: string;
  scale: Record<string, string>;
}
export interface Rubric {
  version: string;
  criteria: RubricCriterion[];
}

export interface LabelItem {
  interaction_id: string;
  rubric_version: string;
  already_labeled_by: number;
  message: string;
  answer: string;
  recommendation: Rec;
  sources: Source[];
}

export interface EvalQuestion {
  id: string;
  topic: string;
  expected: RecType[];
  texts: Record<string, string>;
}
export interface EvalSet {
  reference_persona: Record<string, string>;
  names_by_origin: Record<string, string>;
  questions: EvalQuestion[];
}

/** One bucket of a disaggregated metric. Metric keys vary by endpoint. */
export interface Group {
  value: string;
  label: string;
  n: number;
  [metric: string]: number | string | boolean | null | undefined;
}
export interface AttrGroups {
  label: string;
  groups: Group[];
}

export interface GapInfo {
  gap: number | null;
  best: string | null;
  worst: string | null;
  worst_value?: number;
}
export interface EvalAttribute {
  attribute: string;
  label: string;
  legitimate: boolean;
  alert: boolean;
  accuracy_gap: GapInfo;
  favorable_gap: GapInfo;
  judge_gap: GapInfo;
  groups: Group[];
}
export interface EvalSummary {
  n: number;
  errors: number;
  overall: Record<string, number | null>;
  worst_group_accuracy: number | null;
  threshold: number;
  attributes: EvalAttribute[];
  by_question: {
    question_id: string;
    topic: string;
    expected: RecType[];
    accuracy: number | null;
    reference_type: RecType | null;
    cells: { axis: string; value: string; rec_type: string; correct: boolean; interaction_id: string | null }[];
  }[];
}
export interface EvalRunRow {
  id: string;
  created_at: string;
  status: "running" | "done" | "failed";
  provider: string;
  model: string;
  blinding: number;
  use_judge: number;
  total: number;
  done: number;
  error: string | null;
}
export interface EvalRun extends EvalRunRow {
  config: Record<string, unknown>;
  summary: EvalSummary | null;
}

export interface Suggestion {
  id: number;
  created_at: string;
  interaction_id: string | null;
  reason: string;
  question: string;
  topic: string | null;
  status: "pending" | "approved" | "rejected";
  reviewer: string | null;
  text: string | null;
}

// --- dashboards -------------------------------------------------------------

export interface ProblemDash {
  config: {
    purpose: string;
    true_goal_metrics: { key: string; label: string }[];
    proxy_metrics: { key: string; label: string; warning: string }[];
    decision_sources: { allowed: string[]; excluded: string[] };
    protected_attributes: string[];
    legitimate_attributes: string[];
  };
  overall: Record<string, number | null>;
  last_eval_run: Omit<EvalRunRow, "status" | "total" | "done" | "error" | "use_judge"> | null;
  by_group: Record<string, AttrGroups>;
  proxy_warnings: { count: number; recent: { interaction_id: string; terms: string[]; rationale: string }[] };
}

export interface DataDash {
  kb: {
    chunks: number;
    by_language: Record<string, number>;
    by_readability: Record<string, number>;
    matrix: ({ topic: string } & Record<string, number | string>)[];
    styles: string[];
    gaps: { topic: string; style: string; label: string }[];
  };
  eval_set: { rows: ({ question: string; topic: string } & Record<string, number | string>)[]; styles: string[]; topics: string[] };
  live: { total: number; attributes: Record<string, AttrGroups> };
}

export interface LabelingDash {
  rubric: Rubric;
  n_labels: number;
  n_items: number;
  n_items_multi: number;
  annotators: string[];
  per_criterion: {
    criterion: string;
    n_items: number;
    percent_agreement: number | null;
    alpha: number | null;
    pairwise: { a: string; b: string; n: number; kappa: number | null }[];
  }[];
  leniency: ({ annotator: string; n: number } & Record<string, number | string | null>)[];
  disagreements: { interaction_id: string; message: string; spread: Record<string, number>; scores: Record<string, Record<string, number>> }[];
  by_group: Record<string, Group[]>;
}

export interface DeploymentDash {
  interactions: number;
  auto_rate: number | null;
  route_reasons: { reason: string; label: string; n: number }[];
  queue_pending: number;
  decided: number;
  acceptance_rate: number | null;
  override_rate: number | null;
  rubber_stamp_rate: number | null;
  mean_review_seconds: number | null;
  negative_overridden_rate: number | null;
  rubber_stamp_seconds: number;
  by_group: Record<string, AttrGroups>;
}

export interface FeedbackDash {
  interactions: number;
  feedback: number;
  feedback_coverage: number | null;
  attributes: Record<string, AttrGroups>;
  warnings: string[];
  holdout: { decided: number; human_disagreement_rate: number | null; explanation: string };
  suggestions: Suggestion[];
  auto_learning: boolean;
}
