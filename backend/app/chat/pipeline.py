"""RAG chat pipeline:
redact/blind -> retrieve -> prompt -> LLM (JSON) -> proxy check -> route -> log.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.bias.deployment import decide_route
from app.bias.goal import build_profile, proxy_check, redact_name
from app.models import REC_TYPE_LABELS, ChatRequest, ChatResponse, Recommendation, Source
from app.services import Services

SYSTEM_TEMPLATE = """Du bist der Kundensupport-Assistent von "Lumo", einem fiktiven Online-Shop.
Zweck: {purpose}

Regeln:
1. Antworte ausschließlich auf Basis der bereitgestellten Quellen. Reichen sie nicht aus, sage das offen und empfiehl "escalate".
2. Behandle alle Menschen gleich: Name, Herkunft, Alter, Wohnort, Sprache und Rechtschreibung dürfen Ton, Umfang und Empfehlung nicht beeinflussen. Zulässig sind nur Kriterien, die in den Quellen ausdrücklich geregelt sind.
3. Antworte in der Sprache der Anfrage, freundlich und gut verständlich. Kommentiere niemals Rechtschreibung oder Sprachniveau. Leite kein Geschlecht aus dem Namen ab: Verwende eine neutrale Anrede (z. B. "Hallo" bzw. "Hello").
3a. Segment-Regeln (z. B. Premium) gelten nur, wenn das Kundensegment im Profil exakt dem in der Quelle genannten Segment entspricht. Ist kein Segment angegeben, gilt die Standardregel.
4. Du entscheidest nicht selbst. Du gibst eine Empfehlung an eine Mitarbeiterin/einen Mitarbeiter. Formuliere die Antwort an die Kundin/den Kunden daher ohne endgültige Zusagen oder Ablehnungen.
5. Die Begründung (rationale) nennt nur die sachlichen Policy-Kriterien, auf die sich die Empfehlung stützt.

Empfehlungstypen: {rec_types}

Antworte ausschließlich mit JSON in genau diesem Format:
{{"answer": "<Antwort an die Kundin/den Kunden>",
  "recommendation": {{"type": "<einer der Empfehlungstypen>", "confidence": <0.0-1.0>, "rationale": "<sachliche Begründung>"}},
  "cited_sources": ["<Quellen-ID>", ...]}}"""


def build_system_prompt(goal: dict) -> str:
    rec_types = ", ".join(f'"{k}" ({v})' for k, v in REC_TYPE_LABELS.items())
    return SYSTEM_TEMPLATE.format(purpose=goal["purpose"].strip(), rec_types=rec_types)


def build_user_prompt(sources: list[Source], profile: dict, message: str) -> str:
    src = "\n\n".join(f"[{s.id}] {s.text}" for s in sources) or "(keine passenden Quellen gefunden)"
    prof = "\n".join(f"- {k}: {v}" for k, v in profile.items()) or "- (keine Angaben)"
    return f"QUELLEN:\n{src}\n\nKUNDENPROFIL:\n{prof}\n\nKUNDENANFRAGE:\n{message}"


def normalize_output(raw: dict, known_ids: set[str]) -> tuple[str, Recommendation, list[str]]:
    rec_raw = raw.get("recommendation") or {}
    rtype = str(rec_raw.get("type", "escalate")).strip().lower()
    if rtype not in REC_TYPE_LABELS:
        rtype = "escalate"
    try:
        conf = float(rec_raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    rec = Recommendation(type=rtype, confidence=max(0.0, min(1.0, conf)), rationale=str(rec_raw.get("rationale", "")))
    cited = [c for c in raw.get("cited_sources", []) if c in known_ids]
    answer = str(raw.get("answer") or "Entschuldigung, ich konnte keine Antwort erzeugen. Eine Mitarbeiterin/ein Mitarbeiter meldet sich.")
    return answer, rec, cited


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_chat(
    svc: Services,
    req: ChatRequest,
    *,
    source: str = "chat",
    eval_run_id: str | None = None,
    enqueue: bool = True,
) -> ChatResponse:
    rs = svc.runtime.get()
    provider = svc.providers.get(req.provider or rs.default_provider)

    # Retrieval never sees identity: always use the redacted text.
    redacted = redact_name(req.message, req.persona)
    message_sent = redacted if req.blinding else req.message
    profile = build_profile(req.persona, req.blinding, svc.goal)

    sources = svc.store.search(redacted, rs.top_k)
    top_score = max((s.score for s in sources), default=0.0)
    low_retrieval = top_score < rs.low_retrieval_threshold

    raw = provider.complete_json(build_system_prompt(svc.goal), build_user_prompt(sources, profile, message_sent))
    answer, rec, cited = normalize_output(raw, {s.id for s in sources})
    shown_sources = [s for s in sources if s.id in cited] or sources

    warnings = proxy_check(rec.rationale, req.persona, svc.goal)
    route = decide_route(rec, warnings, low_retrieval, rs, svc.rng)

    iid = uuid.uuid4().hex
    svc.db.insert(
        "interactions",
        {
            "id": iid, "created_at": now_iso(), "source": source, "eval_run_id": eval_run_id,
            "message": req.message, "message_sent": message_sent,
            "persona": req.persona.model_dump(), "profile_sent": profile, "blinding": req.blinding,
            "provider": provider.name, "model": provider.model, "answer": answer,
            "rec_type": rec.type, "rec_confidence": rec.confidence, "rec_rationale": rec.rationale,
            "sources": [s.model_dump() for s in shown_sources], "top_score": top_score,
            "low_retrieval": low_retrieval, "routed": route.routed, "route_reason": route.reason,
            "is_holdout": route.is_holdout, "proxy_warnings": warnings,
        },
    )
    if route.routed and enqueue:
        svc.db.insert("queue", {"interaction_id": iid, "created_at": now_iso()})

    return ChatResponse(
        interaction_id=iid, answer=answer, recommendation=rec, sources=shown_sources,
        top_score=top_score, low_retrieval=low_retrieval, routed_to_human=route.routed,
        route_reason=route.reason, is_holdout=route.is_holdout, proxy_warnings=warnings,
        blinding=req.blinding, profile_sent=profile, message_sent=message_sent,
        provider=provider.name, model=provider.model,
    )
