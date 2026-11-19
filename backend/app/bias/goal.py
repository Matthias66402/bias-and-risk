"""Phase 1 – Problemdefinition.

* Which persona attributes may reach the model (blinding of protected attributes)
* Redaction of the customer's name from the message text
* Proxy check: does the model's *decision rationale* lean on protected/proxy features?
"""
from __future__ import annotations

import re

from app.models import ATTRIBUTES, GROUP_ATTRS, Persona


def build_profile(persona: Persona, blinding: bool, goal: dict) -> dict:
    """Attributes that are actually sent to the LLM (labels, not codes)."""
    allowed = set(goal.get("legitimate_attributes", [])) if blinding else set(GROUP_ATTRS)
    profile = {
        ATTRIBUTES[a]["label"]: ATTRIBUTES[a]["values"].get(getattr(persona, a), getattr(persona, a))
        for a in GROUP_ATTRS
        if a in allowed
    }
    if not blinding:
        profile["Name"] = persona.name
    return profile


def _name_tokens(name: str) -> list[str]:
    tokens = [name.strip()] + [t for t in re.split(r"[\s\-]+", name) if len(t) >= 3]
    return sorted({t for t in tokens if t}, key=len, reverse=True)


def redact_name(message: str, persona: Persona) -> str:
    out = message
    for tok in _name_tokens(persona.name):
        out = re.sub(re.escape(tok), "[Name]", out, flags=re.IGNORECASE)
    return re.sub(r"(\[Name\]\s*)+", "[Name] ", out).strip()


def proxy_check(rationale: str, persona: Persona, goal: dict) -> list[str]:
    """Flags terms in the rationale that suggest a protected attribute drove the decision."""
    text = rationale.lower()
    hits = [t for t in goal.get("proxy_terms", []) if t in text]
    hits += [f"Name '{t}'" for t in _name_tokens(persona.name) if t.lower() in text]
    return sorted(set(hits))


def dashboard(svc) -> dict:
    """Proxy metric (deflection) vs. true goal (resolution, policy accuracy) – overall and per group."""
    from app.bias.groups import disaggregate, rate

    goal = svc.goal
    inter = svc.db.query(
        "SELECT i.id, i.persona, i.routed, i.blinding, i.proxy_warnings, i.rec_rationale, i.created_at, "
        "(SELECT f.resolved FROM feedback f WHERE f.interaction_id = i.id AND f.resolved IS NOT NULL "
        " ORDER BY f.id DESC LIMIT 1) AS resolved "
        "FROM interactions i WHERE i.source = 'chat'"
    )
    last_run = svc.db.one("SELECT id, created_at, provider, model, blinding, summary FROM eval_runs "
                          "WHERE status = 'done' ORDER BY created_at DESC LIMIT 1")
    summary = (last_run or {}).get("summary") or {}

    metrics = {
        "deflection_rate": lambda s: rate(s, lambda r: not r["routed"]),
        "resolution_rate": lambda s: rate(s, lambda r: None if r["resolved"] is None else bool(r["resolved"])),
    }
    warned = [r for r in inter if r["proxy_warnings"]]
    return {
        "config": {k: goal.get(k) for k in ("purpose", "true_goal_metrics", "proxy_metrics", "decision_sources",
                                             "protected_attributes", "legitimate_attributes")},
        "overall": {
            **{k: fn(inter) if inter else None for k, fn in metrics.items()},
            "policy_accuracy": (summary.get("overall") or {}).get("accuracy"),
            "worst_group_accuracy": summary.get("worst_group_accuracy"),
            "blinding_share": rate(inter, lambda r: r["blinding"]),
        },
        "last_eval_run": {k: v for k, v in (last_run or {}).items() if k != "summary"} or None,
        "by_group": {a: {"label": ATTRIBUTES[a]["label"], "groups": disaggregate(inter, a, metrics)} for a in GROUP_ATTRS},
        "proxy_warnings": {
            "count": len(warned),
            "recent": [{"interaction_id": r["id"], "terms": r["proxy_warnings"], "rationale": r["rec_rationale"][:300]}
                       for r in sorted(warned, key=lambda r: r["created_at"], reverse=True)[:10]],
        },
    }
