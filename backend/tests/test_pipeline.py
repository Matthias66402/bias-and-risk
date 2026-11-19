from app.chat.pipeline import run_chat
from app.models import ChatRequest, Persona
from app.rag.ingest import load_kb
from app.config import DATA_DIR

MEHMET = Persona(name="Mehmet Yılmaz", name_origin="tuerkisch", age_group="65+", region="land")


def test_kb_has_metadata():
    chunks = load_kb(DATA_DIR / "kb")
    assert chunks and all({"topic", "language", "readability", "doc"} <= c.metadata.keys() for c in chunks)


def test_retrieval_finds_returns_policy(svc):
    hits = svc.store.search("Rückgabefrist Rücksendung zurückschicken", 3)
    assert any(h.topic == "retouren" for h in hits)


def test_blinding_removes_protected_attributes_and_name(svc):
    resp = run_chat(svc, ChatRequest(message="Hallo, ich bin Mehmet Yılmaz. Jacke zurückschicken?", persona=MEHMET, blinding=True))
    assert "Mehmet" not in resp.message_sent
    assert set(resp.profile_sent) == {"Kundensegment"}  # only the legitimate attribute
    _, user_prompt = svc.providers.get("fake").calls[-1]
    assert "Mehmet" not in user_prompt and "65+" not in user_prompt


def test_without_blinding_profile_is_sent(svc):
    resp = run_chat(svc, ChatRequest(message="Jacke zurückschicken?", persona=MEHMET, blinding=False))
    assert resp.profile_sent["Name"] == "Mehmet Yılmaz"
    assert "Altersgruppe" in resp.profile_sent


def test_negative_recommendation_goes_to_queue(svc):
    resp = run_chat(svc, ChatRequest(message="Bohrmaschine vor 90 Tagen gekauft, benutzt. Zurückgeben?"))
    assert resp.recommendation.type == "deny"
    assert resp.routed_to_human and resp.route_reason == "negative_empfehlung"
    assert svc.db.one("SELECT * FROM queue WHERE interaction_id = ?", (resp.interaction_id,))


def test_positive_high_confidence_is_automatic(svc):
    resp = run_chat(svc, ChatRequest(message="Jacke passt nicht, vor 10 Tagen erhalten. Zurückschicken?"))
    assert resp.recommendation.type == "refund" and not resp.routed_to_human


def test_holdout_routes_positive_cases(svc):
    rs = svc.runtime.get().model_copy(update={"holdout_rate": 1.0})
    svc.runtime.update(rs)
    resp = run_chat(svc, ChatRequest(message="Jacke passt nicht, vor 10 Tagen erhalten. Zurückschicken?"))
    assert resp.routed_to_human and resp.is_holdout


def test_proxy_warning_is_flagged(biased_svc):
    resp = run_chat(biased_svc, ChatRequest(message="Jacke zurück?", persona=MEHMET, blinding=False))
    assert {"alter", "herkunft"} <= set(resp.proxy_warnings)
    assert resp.routed_to_human
