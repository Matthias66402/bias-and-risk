PHASES = ["problem", "data", "labeling", "model", "deployment", "feedback"]


def _chat(client, message, **kw):
    r = client.post("/api/chat", json={"message": message, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def test_chat_queue_decision_flow(client):
    resp = _chat(client, "Bohrmaschine vor 90 Tagen gekauft, benutzt. Zurückgeben?")
    assert resp["routed_to_human"]
    queue = client.get("/api/queue").json()
    item = next(q for q in queue if q["interaction_id"] == resp["interaction_id"])
    assert "persona" not in item and set(item["visible_attributes"]) == {"segment"}

    # rationale is mandatory
    bad = client.post(f"/api/queue/{item['queue_id']}/decision", json={"final_type": "deny", "rationale": "", "reviewer": "a", "review_seconds": 1})
    assert bad.status_code == 422
    ok = client.post(f"/api/queue/{item['queue_id']}/decision",
                     json={"final_type": "goodwill", "rationale": "Kunde hat besondere Umstände geschildert", "reviewer": "a", "review_seconds": 30})
    assert ok.json() == {"accepted": False}
    dash = client.get("/api/dashboard/deployment").json()
    assert dash["override_rate"] == 1.0


def test_labeling_and_agreement(client):
    iid = _chat(client, "Jacke passt nicht, vor 10 Tagen erhalten.")["interaction_id"]
    for annotator, k in (("anna", 3), ("ben", 1)):
        item = client.get("/api/labeling/next", params={"annotator": annotator}).json()
        assert item["interaction_id"] == iid and "persona" not in item
        scores = {"korrektheit": k, "vollstaendigkeit": 3, "ton": 3, "belegt": 2}
        assert client.post("/api/labeling", json={"interaction_id": iid, "annotator": annotator, "scores": scores}).status_code == 200
    agr = client.get("/api/labeling/agreement").json()
    assert agr["n_items_multi"] == 1
    assert agr["disagreements"][0]["interaction_id"] == iid


def test_feedback_creates_suggestion_and_human_approval(client):
    iid = _chat(client, "Kann ich mit Klarna bezahlen?")["interaction_id"]
    r = client.post("/api/feedback", json={"interaction_id": iid, "helpful": False, "resolved": False}).json()
    sid = r["suggestion_id"]
    assert sid
    # approval without human-written text is refused
    assert client.post(f"/api/kb-suggestions/{sid}/decision", json={"approve": True, "reviewer": "anna"}).status_code == 422
    ok = client.post(f"/api/kb-suggestions/{sid}/decision",
                     json={"approve": True, "reviewer": "anna", "topic": "zahlung", "text": "Klarna wird derzeit nicht angeboten."}).json()
    assert ok["status"] == "approved" and ok["kb_chunks"] > 0


def test_all_dashboards(client):
    _chat(client, "Jacke passt nicht, vor 10 Tagen erhalten.", persona={"name": "Li Wei", "name_origin": "ostasiatisch"})
    for phase in PHASES:
        r = client.get(f"/api/dashboard/{phase}")
        assert r.status_code == 200, (phase, r.text)
    data = client.get("/api/dashboard/data").json()
    assert any(g["style"] == "englisch" for g in data["kb"]["gaps"])  # intentional KB gap is reported


def test_eval_endpoint(client):
    r = client.post("/api/eval/counterfactual", json={"provider": "fake", "attributes": ["region"], "question_ids": ["beschaedigt"]})
    assert r.status_code == 200
    run = client.get(f"/api/eval/runs/{r.json()['run_id']}").json()
    assert run["status"] == "done" and run["done"] == run["total"] == 3


def test_settings_validation(client):
    s = client.get("/api/settings").json()
    assert client.put("/api/settings", json={**s, "default_provider": "nope"}).status_code == 422
    assert client.put("/api/settings", json={**s, "holdout_rate": 0.2}).json()["holdout_rate"] == 0.2
