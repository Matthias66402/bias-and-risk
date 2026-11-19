from app.bias.fairness_eval import build_cases, execute_run, start_run
from app.bias.goal import proxy_check, redact_name
from app.bias.labeling import cohen_kappa, krippendorff_alpha_nominal
from app.models import EvalRequest, Persona


def test_cohen_kappa():
    assert cohen_kappa([1, 2, 3, 1], [1, 2, 3, 1]) == 1.0
    assert cohen_kappa([1, 1, 2, 2], [2, 2, 1, 1]) < 0
    assert cohen_kappa([], []) is None


def test_krippendorff_alpha():
    assert krippendorff_alpha_nominal([[1, 1], [2, 2], [3, 3]]) == 1.0
    assert krippendorff_alpha_nominal([[1, 2], [2, 1], [1, 2]]) < 0
    assert krippendorff_alpha_nominal([[1]]) is None


def test_redact_and_proxy_check():
    p = Persona(name="Fatima Al-Hassan")
    assert "Fatima" not in redact_name("Viele Grüße, Fatima Al-Hassan", p)
    goal = {"proxy_terms": ["alter", "herkunft"]}
    assert proxy_check("Wegen des Alters keine Kulanz", p, goal) == ["alter"]
    assert proxy_check("Frist überschritten", p, goal) == []


def test_build_cases_counterfactual(svc):
    cases = build_cases(svc.eval_set, ["name_origin"], ["retoure_in_frist"])
    assert len(cases) == 6  # reference + 5 other names
    assert {c.message.split("\n")[0] for c in cases} == {svc.eval_set["questions"][0]["texts"]["standard"]}
    seg = build_cases(svc.eval_set, ["segment"], ["retoure_knapp_abgelaufen"])
    premium = next(c for c in seg if c.value == "premium")
    assert premium.expected == ["refund", "info"]  # legitimate, policy-defined difference


def _run(svc, blinding):
    req = EvalRequest(provider="fake", blinding=blinding, attributes=["name_origin", "age_group"], use_judge=True)
    run_id, cases = start_run(svc, req)
    execute_run(svc, run_id, req, cases)
    return svc.db.one("SELECT * FROM eval_runs WHERE id = ?", (run_id,))


def test_counterfactual_detects_bias_without_blinding(biased_svc):
    run = _run(biased_svc, blinding=False)
    assert run["status"] == "done"
    attrs = {a["attribute"]: a for a in run["summary"]["attributes"]}
    assert attrs["name_origin"]["alert"] and attrs["age_group"]["alert"]
    assert run["summary"]["worst_group_accuracy"] < run["summary"]["overall"]["accuracy"]


def test_blinding_removes_bias(biased_svc):
    run = _run(biased_svc, blinding=True)
    attrs = {a["attribute"]: a for a in run["summary"]["attributes"]}
    assert not attrs["name_origin"]["alert"] and not attrs["age_group"]["alert"]
