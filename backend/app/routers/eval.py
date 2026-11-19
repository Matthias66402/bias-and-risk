from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.bias.fairness_eval import build_cases, execute_run, start_run
from app.llm.providers import ProviderError
from app.models import ATTRIBUTES, EvalRequest
from app.services import Services, get_services

router = APIRouter(prefix="/api/eval", tags=["eval"])


@router.get("/questions")
def questions(svc: Services = Depends(get_services)) -> dict:
    return svc.eval_set


@router.post("/counterfactual")
def counterfactual(req: EvalRequest, bg: BackgroundTasks, svc: Services = Depends(get_services)) -> dict:
    unknown = set(req.attributes) - set(ATTRIBUTES)
    if unknown:
        raise HTTPException(422, f"Unbekannte Merkmale: {sorted(unknown)}")
    try:
        run_id, cases = start_run(svc, req)
    except ProviderError as e:
        raise HTTPException(502, str(e))
    bg.add_task(execute_run, svc, run_id, req, cases)
    return {"run_id": run_id, "total": len(cases)}


@router.post("/estimate")
def estimate(req: EvalRequest, svc: Services = Depends(get_services)) -> dict:
    n = len(build_cases(svc.eval_set, req.attributes, req.question_ids, req.repetitions))
    return {"cases": n, "llm_calls": n * (2 if req.use_judge else 1)}


@router.get("/runs")
def runs(svc: Services = Depends(get_services)) -> list[dict]:
    return svc.db.query("SELECT id, created_at, status, provider, model, blinding, use_judge, total, done, error "
                        "FROM eval_runs ORDER BY created_at DESC LIMIT 50")


@router.get("/runs/{run_id}")
def run(run_id: str, svc: Services = Depends(get_services)) -> dict:
    row = svc.db.one("SELECT * FROM eval_runs WHERE id = ?", (run_id,))
    if not row:
        raise HTTPException(404, "Run nicht gefunden")
    return row
