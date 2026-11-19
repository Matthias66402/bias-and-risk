from fastapi import APIRouter, Depends, HTTPException

from app.bias.deployment import ROUTE_REASON_LABELS
from app.bias.feedback_loop import create_suggestion, record_feedback
from app.chat.pipeline import run_chat
from app.llm.providers import ProviderError
from app.models import ATTRIBUTES, FAVORABLE_TYPES, REC_TYPE_LABELS, ChatRequest, ChatResponse, FeedbackIn
from app.services import Services, get_services

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, svc: Services = Depends(get_services)) -> ChatResponse:
    try:
        resp = run_chat(svc, req)
    except ProviderError as e:
        raise HTTPException(502, str(e))
    if resp.low_retrieval:  # Phase 2/6: KB gap -> suggestion for a human, never auto-filled
        create_suggestion(svc, resp.interaction_id, "kb_luecke", req.message, resp.sources[0].topic if resp.sources else None)
    return resp


@router.post("/feedback")
def feedback(fb: FeedbackIn, svc: Services = Depends(get_services)) -> dict:
    try:
        return record_feedback(svc, fb)
    except KeyError:
        raise HTTPException(404, "Interaktion nicht gefunden")


@router.get("/meta")
def meta(svc: Services = Depends(get_services)) -> dict:
    return {
        "attributes": ATTRIBUTES,
        "rec_types": REC_TYPE_LABELS,
        "favorable_types": sorted(FAVORABLE_TYPES),
        "route_reasons": ROUTE_REASON_LABELS,
        "protected_attributes": svc.goal.get("protected_attributes", []),
        "legitimate_attributes": svc.goal.get("legitimate_attributes", []),
        "names_by_origin": svc.eval_set.get("names_by_origin", {}),
    }
