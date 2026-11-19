"""Phase 3 – Kennzeichnung: Wessen Urteil wird zum Label?

* explicit, versioned rubric (data/rubric_v1.yaml)
* annotators never see persona attributes (blind labeling)
* agreement: pairwise Cohen's kappa + Krippendorff's alpha (nominal) per criterion
* annotator leniency and disagreement list for rubric clarification
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from app.bias.goal import redact_name
from app.bias.groups import disaggregate, mean
from app.models import ATTRIBUTES, Persona
from app.services import Services


def cohen_kappa(a: list, b: list) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    if pe == 1:
        return 1.0 if po == 1 else 0.0
    return round((po - pe) / (1 - pe), 4)


def krippendorff_alpha_nominal(units: list[list]) -> float | None:
    """units: list of rating lists (one list per item; items with <2 ratings are ignored)."""
    coinc: dict[tuple, float] = defaultdict(float)
    for vals in units:
        m = len(vals)
        if m < 2:
            continue
        for i, j in combinations(range(m), 2):
            coinc[(vals[i], vals[j])] += 1 / (m - 1)
            coinc[(vals[j], vals[i])] += 1 / (m - 1)
    if not coinc:
        return None
    n_c: dict = defaultdict(float)
    for (c, _), v in coinc.items():
        n_c[c] += v
    n = sum(n_c.values())
    d_o = sum(v for (c, k), v in coinc.items() if c != k)
    d_e = sum(n_c[c] * n_c[k] for c in n_c for k in n_c if c != k) / (n - 1)
    if d_e == 0:
        return 1.0
    return round(1 - d_o / d_e, 4)


def next_item(svc: Services, annotator: str) -> dict | None:
    version = svc.rubric["version"]
    row = svc.db.one(
        """
        SELECT i.*, (SELECT COUNT(*) FROM labels l WHERE l.interaction_id = i.id AND l.rubric_version = ?) AS n_labels
        FROM interactions i
        WHERE NOT EXISTS (SELECT 1 FROM labels l WHERE l.interaction_id = i.id AND l.annotator = ? AND l.rubric_version = ?)
        ORDER BY n_labels DESC, CASE i.source WHEN 'chat' THEN 0 ELSE 1 END, i.created_at DESC
        LIMIT 1
        """,
        (version, annotator, version),
    )
    # n_labels DESC: complete partially labeled items first -> agreement becomes measurable sooner
    if not row:
        return None
    persona = Persona(**row["persona"])
    return {
        "interaction_id": row["id"],
        "rubric_version": version,
        "already_labeled_by": row["n_labels"],
        # blind labeling: always the redacted text, never the persona
        "message": redact_name(row["message"], persona),
        "answer": row["answer"],
        "recommendation": {"type": row["rec_type"], "confidence": row["rec_confidence"], "rationale": row["rec_rationale"]},
        "sources": row["sources"],
    }


def _labels(svc: Services) -> list[dict]:
    return svc.db.query(
        "SELECT l.*, i.persona, i.message FROM labels l JOIN interactions i ON i.id = l.interaction_id WHERE l.rubric_version = ?",
        (svc.rubric["version"],),
    )


def agreement(svc: Services) -> dict:
    labels = _labels(svc)
    criteria = [c["key"] for c in svc.rubric["criteria"]]
    by_item: dict[str, dict[str, dict]] = defaultdict(dict)
    for l in labels:
        by_item[l["interaction_id"]][l["annotator"]] = l["scores"]
    multi = {k: v for k, v in by_item.items() if len(v) >= 2}
    annotators = sorted({l["annotator"] for l in labels})

    per_criterion = []
    for c in criteria:
        units = [[s[c] for s in raters.values() if c in s] for raters in multi.values()]
        units = [u for u in units if len(u) >= 2]
        pairwise = []
        for a, b in combinations(annotators, 2):
            common = [k for k, r in by_item.items() if a in r and b in r and c in r[a] and c in r[b]]
            if common:
                pairwise.append({"a": a, "b": b, "n": len(common),
                                 "kappa": cohen_kappa([by_item[k][a][c] for k in common], [by_item[k][b][c] for k in common])})
        per_criterion.append({
            "criterion": c,
            "n_items": len(units),
            "percent_agreement": round(sum(len(set(u)) == 1 for u in units) / len(units), 4) if units else None,
            "alpha": krippendorff_alpha_nominal(units),
            "pairwise": pairwise,
        })

    leniency = []
    for a in annotators:
        mine = [l["scores"] for l in labels if l["annotator"] == a]
        leniency.append({"annotator": a, "n": len(mine), **{c: mean([s.get(c) for s in mine]) for c in criteria}})

    disagreements = []
    for iid, raters in multi.items():
        spread = {c: max(s[c] for s in raters.values() if c in s) - min(s[c] for s in raters.values() if c in s)
                  for c in criteria if sum(c in s for s in raters.values()) >= 2}
        if any(v >= 2 for v in spread.values()) or spread.get("korrektheit", 0) >= 1:
            msg = next(l["message"] for l in labels if l["interaction_id"] == iid)
            disagreements.append({"interaction_id": iid, "message": msg[:200], "spread": spread, "scores": raters})

    # Average label per persona group (labels were given blind, so differences reflect the answers)
    by_group = {}
    for attr in ATTRIBUTES:
        by_group[attr] = disaggregate(labels, attr, {c: (lambda sub, c=c: mean([l["scores"].get(c) for l in sub])) for c in criteria})

    return {
        "rubric": svc.rubric,
        "n_labels": len(labels),
        "n_items": len(by_item),
        "n_items_multi": len(multi),
        "annotators": annotators,
        "per_criterion": per_criterion,
        "leniency": leniency,
        "disagreements": disagreements,
        "by_group": by_group,
    }
