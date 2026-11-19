"""Phase 2 – Datensammlung: Wer ist vertreten oder fehlt?

Three views:
1. Knowledge base: which topic x language x readability combinations exist?
2. Eval set: which topic x language style combinations are tested?
3. Live traffic: group representation and retrieval quality per group.
"""
from __future__ import annotations

from collections import Counter

from app.bias.groups import disaggregate, mean, rate
from app.models import ATTRIBUTES, GROUP_ATTRS
from app.services import Services

# Which KB variant serves which customer language style
STYLE_NEEDS = {
    "standard": {"language": "de", "readability": None},
    "tippfehler": {"language": "de", "readability": None},
    "einfach": {"language": "de", "readability": "einfach"},
    "englisch": {"language": "en", "readability": None},
}


def kb_coverage(metadata: list[dict]) -> dict:
    topics = sorted({m.get("topic", "?") for m in metadata})
    chunk_counts = Counter((m.get("topic"), m.get("language"), m.get("readability")) for m in metadata)
    matrix = []
    gaps = []
    for t in topics:
        row = {"topic": t}
        for style, need in STYLE_NEEDS.items():
            n = sum(
                c for (tt, lang, read), c in chunk_counts.items()
                if tt == t and lang == need["language"] and (need["readability"] is None or read == need["readability"])
            )
            row[style] = n
            if n == 0:
                gaps.append({"topic": t, "style": style, "label": ATTRIBUTES["language_style"]["values"][style]})
        matrix.append(row)
    return {
        "chunks": len(metadata),
        "by_language": dict(Counter(m.get("language") for m in metadata)),
        "by_readability": dict(Counter(m.get("readability") for m in metadata)),
        "matrix": matrix,
        "styles": list(STYLE_NEEDS),
        "gaps": gaps,
    }


def eval_coverage(eval_set: dict) -> dict:
    styles = list(ATTRIBUTES["language_style"]["values"])
    rows = [{"question": q["id"], "topic": q["topic"], **{s: int(s in q.get("texts", {})) for s in styles}} for q in eval_set["questions"]]
    tested_topics = {q["topic"] for q in eval_set["questions"]}
    return {"rows": rows, "styles": styles, "topics": sorted(tested_topics), "names": eval_set.get("names_by_origin", {})}


def live_coverage(svc: Services) -> dict:
    rs = svc.runtime.get()
    rows = svc.db.query("SELECT persona, top_score, low_retrieval, rec_type FROM interactions WHERE source = 'chat'")
    total = len(rows)
    out = {}
    for attr in GROUP_ATTRS:
        groups = disaggregate(rows, attr, {
            "low_retrieval_rate": lambda s: rate(s, lambda r: r["low_retrieval"]),
            "escalate_rate": lambda s: rate(s, lambda r: r["rec_type"] == "escalate"),
            "mean_top_score": lambda s: mean([r["top_score"] for r in s]),
        })
        overall_low = rate(rows, lambda r: r["low_retrieval"]) or 0.0
        for g in groups:
            g["share"] = round(g["n"] / total, 4) if total else 0.0
            g["underrepresented"] = total > 0 and g["share"] < rs.min_group_share
            g["retrieval_gap"] = g["low_retrieval_rate"] is not None and g["low_retrieval_rate"] > overall_low + 0.1
        out[attr] = {"label": ATTRIBUTES[attr]["label"], "groups": groups}
    return {"total": total, "attributes": out}


def dashboard(svc: Services) -> dict:
    return {
        "kb": kb_coverage(svc.store.all_metadata()),
        "eval_set": eval_coverage(svc.eval_set),
        "live": live_coverage(svc),
    }
