"""Phase 5 – Human-in-the-loop queue. Reviewers see the redacted request and only
legitimate attributes (segment), so their own decisions are blinded as well."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from app.bias.goal import redact_name
from app.chat.pipeline import now_iso
from app.models import DecisionIn, Persona
from app.services import Services, get_services

router = APIRouter(prefix="/api/queue", tags=["queue"])


def _view(row: dict, legitimate: list[str]) -> dict:
    persona = Persona(**row["persona"])
    return {
        "queue_id": row["qid"], "interaction_id": row["interaction_id"], "status": row["status"],
        "created_at": row["q_created_at"], "route_reason": row["route_reason"], "is_holdout": bool(row["is_holdout"]),
        "message": redact_name(row["message"], persona),
        "visible_attributes": {a: getattr(persona, a) for a in legitimate},
        "answer": row["answer"],
        "recommendation": {"type": row["rec_type"], "confidence": row["rec_confidence"], "rationale": row["rec_rationale"]},
        "sources": row["sources"], "proxy_warnings": row["proxy_warnings"],
        "decision": None if row["status"] == "pending" else {
            "final_type": row["final_type"], "accepted": bool(row["accepted"]), "rationale": row["rationale"],
            "reviewer": row["reviewer"], "review_seconds": row["review_seconds"], "decided_at": row["decided_at"],
        },
    }


SELECT = ("SELECT q.id AS qid, q.created_at AS q_created_at, q.*, i.* FROM queue q "
          "JOIN interactions i ON i.id = q.interaction_id ")


@router.get("")
def list_queue(status: Literal["pending", "decided"] = "pending", svc: Services = Depends(get_services)) -> list[dict]:
    rows = svc.db.query(SELECT + "WHERE q.status = ? ORDER BY q.created_at DESC LIMIT 200", (status,))
    return [_view(r, svc.goal.get("legitimate_attributes", [])) for r in rows]


@router.post("/{queue_id}/decision")
def decide(queue_id: int, d: DecisionIn, svc: Services = Depends(get_services)) -> dict:
    row = svc.db.one(SELECT + "WHERE q.id = ?", (queue_id,))
    if not row:
        raise HTTPException(404, "Queue-Eintrag nicht gefunden")
    if row["status"] != "pending":
        raise HTTPException(409, "Bereits entschieden")
    accepted = d.final_type == row["rec_type"]
    svc.db.update("queue", "id", queue_id, {
        "status": "decided", "decided_at": now_iso(), "final_type": d.final_type, "accepted": accepted,
        "rationale": d.rationale, "reviewer": d.reviewer, "review_seconds": d.review_seconds,
    })
    return {"accepted": accepted}
