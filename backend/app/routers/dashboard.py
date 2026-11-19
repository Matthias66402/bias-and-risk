from typing import Literal

from fastapi import APIRouter, Depends

from app.bias import coverage, deployment, feedback_loop, goal, labeling
from app.services import Services, get_services

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

Phase = Literal["problem", "data", "labeling", "model", "deployment", "feedback"]


@router.get("/{phase}")
def dashboard(phase: Phase, svc: Services = Depends(get_services)) -> dict:
    if phase == "problem":
        return goal.dashboard(svc)
    if phase == "data":
        return coverage.dashboard(svc)
    if phase == "labeling":
        return labeling.agreement(svc)
    if phase == "deployment":
        return deployment.dashboard(svc)
    if phase == "feedback":
        return feedback_loop.dashboard(svc)
    # model: the latest finished counterfactual runs (summaries are precomputed)
    runs = svc.db.query("SELECT * FROM eval_runs WHERE status = 'done' ORDER BY created_at DESC LIMIT 10")
    return {"runs": runs}
