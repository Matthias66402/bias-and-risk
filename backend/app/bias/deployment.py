"""Phase 5 – Einsatz: Wie verwenden Menschen die Punktzahl?

The model only *recommends*. Anything negative, uncertain, suspicious or randomly
sampled (holdout) is routed to a human. Humans must give their own rationale; we
measure how often they just rubber-stamp the recommendation (automation bias).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from app.config import RuntimeSettings
from app.models import NEGATIVE_TYPES, Recommendation

ROUTE_REASON_LABELS = {
    "negative_empfehlung": "Negative Empfehlung – nie automatisch",
    "eskalation": "Modell eskaliert selbst",
    "proxy_warnung": "Begründung nutzt Proxy-Merkmale",
    "niedrige_konfidenz": "Konfidenz unter Schwellwert",
    "kb_luecke": "Wissensbasis deckt Anfrage schlecht ab",
    "holdout": "Zufalls-Holdout (Kontrollstichprobe)",
    "automatisch": "Automatisch beantwortet",
}

RUBBER_STAMP_SECONDS = 5.0


@dataclass
class RouteDecision:
    routed: bool
    reason: str
    is_holdout: bool = False


def decide_route(
    rec: Recommendation,
    proxy_warnings: list[str],
    low_retrieval: bool,
    rs: RuntimeSettings,
    rng: random.Random,
) -> RouteDecision:
    if rec.type in NEGATIVE_TYPES:
        return RouteDecision(True, "negative_empfehlung")
    if rec.type == "escalate":
        return RouteDecision(True, "eskalation")
    if proxy_warnings:
        return RouteDecision(True, "proxy_warnung")
    if rec.confidence < rs.confidence_threshold:
        return RouteDecision(True, "niedrige_konfidenz")
    if low_retrieval:
        return RouteDecision(True, "kb_luecke")
    if rng.random() < rs.holdout_rate:
        return RouteDecision(True, "holdout", is_holdout=True)
    return RouteDecision(False, "automatisch")


def is_rubber_stamp(accepted: bool, review_seconds: float) -> bool:
    return bool(accepted) and review_seconds < RUBBER_STAMP_SECONDS


def dashboard(svc) -> dict:
    from collections import Counter

    from app.bias.groups import disaggregate, mean, rate
    from app.models import ATTRIBUTES, FAVORABLE_TYPES, GROUP_ATTRS

    inter = svc.db.query("SELECT id, persona, routed, route_reason, rec_type FROM interactions WHERE source = 'chat'")
    decided = svc.db.query(
        "SELECT q.*, i.persona, i.rec_type, i.route_reason FROM queue q JOIN interactions i ON i.id = q.interaction_id "
        "WHERE q.status = 'decided'"
    )
    pending = svc.db.one("SELECT COUNT(*) AS n FROM queue WHERE status = 'pending'")["n"]

    reasons = Counter(r["route_reason"] for r in inter)
    by_group = {}
    for attr in GROUP_ATTRS:
        routed = {g["value"]: g for g in disaggregate(inter, attr, {"routed_rate": lambda s: rate(s, lambda r: r["routed"])})}
        human = disaggregate(decided, attr, {
            "override_rate": lambda s: rate(s, lambda r: not r["accepted"]),
            "human_favorable_rate": lambda s: rate(s, lambda r: r["final_type"] in FAVORABLE_TYPES),
            "model_favorable_rate": lambda s: rate(s, lambda r: r["rec_type"] in FAVORABLE_TYPES),
        })
        by_group[attr] = {
            "label": ATTRIBUTES[attr]["label"],
            "groups": [{**h, "routed_rate": routed[h["value"]]["routed_rate"], "interactions": routed[h["value"]]["n"]} for h in human],
        }

    return {
        "interactions": len(inter),
        "auto_rate": rate(inter, lambda r: not r["routed"]),
        "route_reasons": [{"reason": k, "label": ROUTE_REASON_LABELS.get(k, k), "n": v} for k, v in reasons.most_common()],
        "queue_pending": pending,
        "decided": len(decided),
        "acceptance_rate": rate(decided, lambda r: r["accepted"]),
        "override_rate": rate(decided, lambda r: not r["accepted"]),
        "rubber_stamp_rate": rate(decided, lambda r: is_rubber_stamp(r["accepted"], r["review_seconds"] or 0)),
        "mean_review_seconds": mean([r["review_seconds"] for r in decided]),
        "negative_overridden_rate": rate([r for r in decided if r["rec_type"] in NEGATIVE_TYPES], lambda r: not r["accepted"]),
        "rubber_stamp_seconds": RUBBER_STAMP_SECONDS,
        "by_group": by_group,
    }
