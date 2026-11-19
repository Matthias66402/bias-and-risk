"""Phase 6 – Rückkopplung: Formt das System seine künftigen Daten?

* Feedback is stored with group metadata, and we check whether "success data"
  comes from all groups or only a few.
* Nothing is learned automatically: KB gaps become *suggestions* that a human must
  write and approve before they enter the knowledge base.
* The random holdout (Phase 5) shows how often humans disagree with cases the bot
  would otherwise have closed itself, i.e. ground truth the loop would never produce.
"""
from __future__ import annotations

import re

from app.bias.groups import disaggregate, rate
from app.chat.pipeline import now_iso
from app.models import ATTRIBUTES, GROUP_ATTRS, FeedbackIn, SuggestionDecisionIn
from app.rag.ingest import load_kb
from app.services import Services

SUGGESTION_DIR = "vorschlaege"


def record_feedback(svc: Services, fb: FeedbackIn) -> dict:
    inter = svc.db.one("SELECT id, message, low_retrieval, sources FROM interactions WHERE id = ?", (fb.interaction_id,))
    if not inter:
        raise KeyError(fb.interaction_id)
    fid = svc.db.insert("feedback", {**fb.model_dump(), "created_at": now_iso()})
    suggestion_id = None
    if not fb.helpful:
        topic = inter["sources"][0]["topic"] if inter["sources"] else None
        suggestion_id = create_suggestion(svc, inter["id"], "negatives_feedback", inter["message"], topic)
    return {"feedback_id": fid, "suggestion_id": suggestion_id}


def create_suggestion(svc: Services, interaction_id: str | None, reason: str, question: str, topic: str | None) -> int:
    existing = svc.db.one("SELECT id FROM kb_suggestions WHERE interaction_id = ? AND status = 'pending'", (interaction_id,))
    if existing:
        return existing["id"]
    return svc.db.insert("kb_suggestions", {
        "created_at": now_iso(), "interaction_id": interaction_id, "reason": reason, "question": question, "topic": topic,
    })


def decide_suggestion(svc: Services, sid: int, d: SuggestionDecisionIn) -> dict:
    sug = svc.db.one("SELECT * FROM kb_suggestions WHERE id = ?", (sid,))
    if not sug or sug["status"] != "pending":
        raise KeyError(sid)
    if d.approve and not (d.text and d.text.strip()):
        raise ValueError("Für die Freigabe muss ein Mensch den KB-Text verfassen.")
    data = {"status": "approved" if d.approve else "rejected", "reviewer": d.reviewer, "decided_at": now_iso(),
            "text": d.text, "topic": d.topic or sug["topic"]}
    svc.db.update("kb_suggestions", "id", sid, data)
    chunks = None
    if d.approve:
        folder = svc.kb_dir / SUGGESTION_DIR
        folder.mkdir(parents=True, exist_ok=True)
        title = re.sub(r"\s+", " ", sug["question"]).strip()[:80].replace('"', "'")
        (folder / f"vorschlag_{sid}.md").write_text(
            f'---\ntitle: "Ergänzung: {title}"\ntopic: {data["topic"] or "sonstiges"}\nlanguage: de\nreadability: standard\n'
            f"audience: alle\nreviewed_by: {d.reviewer}\n---\n\n## Antwort\n{d.text.strip()}\n",
            encoding="utf-8",
        )
        chunks = svc.store.rebuild(load_kb(svc.kb_dir))
    return {"status": data["status"], "kb_chunks": chunks}


def dashboard(svc: Services) -> dict:
    inter = svc.db.query("SELECT id, persona, routed, is_holdout FROM interactions WHERE source = 'chat'")
    fb = svc.db.query("SELECT f.*, i.persona FROM feedback f JOIN interactions i ON i.id = f.interaction_id WHERE i.source = 'chat'")
    total_i, total_f = len(inter), len(fb)

    attributes = {}
    warnings = []
    for attr in GROUP_ATTRS:
        gi = {g["value"]: g for g in disaggregate(inter, attr, {})}
        gf = disaggregate(fb, attr, {
            "helpful_rate": lambda s: rate(s, lambda r: r["helpful"]),
            "resolved_rate": lambda s: rate(s, lambda r: r["resolved"]),
        })
        groups = []
        for g in gf:
            share_i = gi[g["value"]]["n"] / total_i if total_i else 0.0
            share_f = g["n"] / total_f if total_f else 0.0
            ratio = round(share_f / share_i, 3) if share_i else None
            groups.append({**g, "interactions": gi[g["value"]]["n"], "interaction_share": round(share_i, 4),
                           "feedback_share": round(share_f, 4), "representation_ratio": ratio})
            if ratio is not None and total_f >= 5 and ratio < 0.5:
                warnings.append(f"{ATTRIBUTES[attr]['label']} = {g['label']}: nur {ratio:.0%} des erwarteten Feedback-Anteils")
        attributes[attr] = {"label": ATTRIBUTES[attr]["label"], "groups": groups}

    holdout = svc.db.query(
        "SELECT q.accepted FROM queue q JOIN interactions i ON i.id = q.interaction_id WHERE i.is_holdout = 1 AND q.status = 'decided'"
    )
    suggestions = svc.db.query("SELECT * FROM kb_suggestions ORDER BY created_at DESC")
    return {
        "interactions": total_i,
        "feedback": total_f,
        "feedback_coverage": round(total_f / total_i, 4) if total_i else None,
        "attributes": attributes,
        "warnings": warnings,
        "holdout": {
            "decided": len(holdout),
            "human_disagreement_rate": rate(holdout, lambda r: not r["accepted"]),
            "explanation": "Anteil der Zufalls-Holdout-Fälle, in denen Menschen anders entschieden haben als das Modell – "
                           "Schätzung der Fehlerrate bei sonst automatisch abgeschlossenen Fällen.",
        },
        "suggestions": suggestions,
        "auto_learning": False,
    }
