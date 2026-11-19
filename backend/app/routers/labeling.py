from fastapi import APIRouter, Depends, HTTPException

from app.bias.labeling import agreement, next_item
from app.chat.pipeline import now_iso
from app.models import LabelIn
from app.services import Services, get_services

router = APIRouter(prefix="/api/labeling", tags=["labeling"])


@router.get("/rubric")
def rubric(svc: Services = Depends(get_services)) -> dict:
    return svc.rubric


@router.get("/next")
def next_(annotator: str, svc: Services = Depends(get_services)) -> dict | None:
    return next_item(svc, annotator)


@router.post("")
def submit(label: LabelIn, svc: Services = Depends(get_services)) -> dict:
    criteria = {c["key"]: c for c in svc.rubric["criteria"]}
    if set(label.scores) != set(criteria):
        raise HTTPException(422, f"Erwartete Kriterien: {sorted(criteria)}")
    for k, v in label.scores.items():
        if v not in {int(s) for s in criteria[k]["scale"]}:
            raise HTTPException(422, f"Ungültiger Wert {v} für {k}")
    if not svc.db.one("SELECT id FROM interactions WHERE id = ?", (label.interaction_id,)):
        raise HTTPException(404, "Interaktion nicht gefunden")
    svc.db.execute(
        "INSERT OR REPLACE INTO labels (interaction_id, annotator, rubric_version, scores, comment, created_at) VALUES (?,?,?,?,?,?)",
        (label.interaction_id, label.annotator, svc.rubric["version"], label.scores, label.comment, now_iso()),
    )
    return {"ok": True}


@router.get("/agreement")
def agreement_(svc: Services = Depends(get_services)) -> dict:
    return agreement(svc)
