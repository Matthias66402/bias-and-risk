from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from app.bias.feedback_loop import decide_suggestion
from app.config import RuntimeSettings
from app.models import SuggestionDecisionIn
from app.rag.ingest import load_kb
from app.services import Services, get_services

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/admin/ingest")
def ingest(svc: Services = Depends(get_services)) -> dict:
    n = svc.store.rebuild(load_kb(svc.kb_dir))
    return {"chunks": n, "embedder": svc.store.embedder.name}


@router.get("/admin/status")
def status(svc: Services = Depends(get_services)) -> dict:
    return {"chunks": svc.store.count(), "embedder": svc.store.embedder.name, "providers": svc.providers.available()}


@router.get("/settings", response_model=RuntimeSettings)
def get_settings(svc: Services = Depends(get_services)) -> RuntimeSettings:
    return svc.runtime.get()


@router.put("/settings", response_model=RuntimeSettings)
def put_settings(new: RuntimeSettings, svc: Services = Depends(get_services)) -> RuntimeSettings:
    names = {p["name"] for p in svc.providers.available()}
    for p in (new.default_provider, new.judge_provider):
        if p and p not in names:
            raise HTTPException(422, f"Provider '{p}' nicht konfiguriert. Verfügbar: {sorted(names)}")
    return svc.runtime.update(new)


@router.get("/providers")
def providers(svc: Services = Depends(get_services)) -> list[dict]:
    return svc.providers.available()


@router.get("/kb-suggestions")
def suggestions(status: Literal["pending", "approved", "rejected"] | None = None, svc: Services = Depends(get_services)) -> list[dict]:
    if status:
        return svc.db.query("SELECT * FROM kb_suggestions WHERE status = ? ORDER BY created_at DESC", (status,))
    return svc.db.query("SELECT * FROM kb_suggestions ORDER BY created_at DESC")


@router.post("/kb-suggestions/{sid}/decision")
def decide(sid: int, d: SuggestionDecisionIn, svc: Services = Depends(get_services)) -> dict:
    try:
        return decide_suggestion(svc, sid, d)
    except KeyError:
        raise HTTPException(404, "Vorschlag nicht gefunden oder bereits entschieden")
    except ValueError as e:
        raise HTTPException(422, str(e))
