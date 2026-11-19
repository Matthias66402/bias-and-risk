"""Pydantic API schemas and domain vocabulary."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Vocabulary -----------------------------------------------------------------

RecType = Literal["refund", "replacement", "goodwill", "info", "deny", "escalate"]

REC_TYPE_LABELS: dict[str, str] = {
    "refund": "Erstattung",
    "replacement": "Ersatzlieferung",
    "goodwill": "Kulanz",
    "info": "Reine Auskunft",
    "deny": "Ablehnung",
    "escalate": "An Mitarbeiter:in",
}
FAVORABLE_TYPES = {"refund", "replacement", "goodwill"}
NEGATIVE_TYPES = {"deny"}

# Persona attributes used for monitoring / counterfactual tests.
ATTRIBUTES: dict[str, dict] = {
    "name_origin": {
        "label": "Namensherkunft (wahrgenommen)",
        "values": {
            "deutsch": "deutsch", "tuerkisch": "türkisch", "arabisch": "arabisch",
            "osteuropaeisch": "osteuropäisch", "westafrikanisch": "westafrikanisch", "ostasiatisch": "ostasiatisch",
        },
    },
    "language_style": {
        "label": "Sprachstil",
        "values": {"standard": "Standarddeutsch", "einfach": "Einfache Sprache", "tippfehler": "Viele Tippfehler", "englisch": "Englisch"},
    },
    "segment": {
        "label": "Kundensegment",
        "values": {"neu": "Neukunde", "stamm": "Stammkunde", "premium": "Premium"},
    },
    "age_group": {
        "label": "Altersgruppe",
        "values": {"18-29": "18–29", "30-49": "30–49", "50-64": "50–64", "65+": "65+"},
    },
    "region": {
        "label": "Region",
        "values": {"stadt": "Großstadt", "land": "Ländlich", "ausland_eu": "EU-Ausland"},
    },
}
GROUP_ATTRS = list(ATTRIBUTES)


# --- Chat -----------------------------------------------------------------------

class Persona(BaseModel):
    name: str = "Max Müller"
    name_origin: str = "deutsch"
    language_style: str = "standard"
    segment: str = "stamm"
    age_group: str = "30-49"
    region: str = "stadt"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    persona: Persona = Persona()
    blinding: bool = True
    provider: str | None = None


class Source(BaseModel):
    id: str
    title: str
    topic: str
    score: float
    text: str


class Recommendation(BaseModel):
    type: RecType
    confidence: float
    rationale: str


class ChatResponse(BaseModel):
    interaction_id: str
    answer: str
    recommendation: Recommendation
    sources: list[Source]
    top_score: float
    low_retrieval: bool
    routed_to_human: bool
    route_reason: str
    is_holdout: bool
    proxy_warnings: list[str]
    blinding: bool
    profile_sent: dict
    message_sent: str
    provider: str
    model: str


class FeedbackIn(BaseModel):
    interaction_id: str
    helpful: bool
    resolved: bool | None = None
    comment: str | None = Field(None, max_length=2000)


# --- Queue (Phase 5) ------------------------------------------------------------

class DecisionIn(BaseModel):
    final_type: RecType
    rationale: str = Field(min_length=10, description="Pflicht: eigene Begründung der Mitarbeiter:in")
    reviewer: str = Field(min_length=1)
    review_seconds: float = Field(ge=0)


# --- Labeling (Phase 3) ---------------------------------------------------------

class LabelIn(BaseModel):
    interaction_id: str
    annotator: str = Field(min_length=1)
    scores: dict[str, int]
    comment: str | None = None


# --- Eval (Phase 4) -------------------------------------------------------------

class EvalRequest(BaseModel):
    provider: str | None = None
    blinding: bool = False
    use_judge: bool = False
    attributes: list[str] = Field(default_factory=lambda: list(GROUP_ATTRS))
    question_ids: list[str] | None = None
    repetitions: int = Field(1, ge=1, le=5)


# --- KB suggestions (Phase 6) ---------------------------------------------------

class SuggestionDecisionIn(BaseModel):
    approve: bool
    reviewer: str = Field(min_length=1)
    topic: str | None = None
    text: str | None = Field(None, description="Von Menschen verfasster KB-Text (Pflicht bei approve)")
