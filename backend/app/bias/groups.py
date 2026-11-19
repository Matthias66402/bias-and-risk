"""Helpers for disaggregated (per-group) metrics."""
from __future__ import annotations

from typing import Callable

from app.models import ATTRIBUTES

Metric = Callable[[list[dict]], float | None]


def rate(rows: list[dict], pred: Callable[[dict], bool | None]) -> float | None:
    """Share of rows where pred is True; rows where pred returns None are ignored."""
    vals = [pred(r) for r in rows]
    vals = [v for v in vals if v is not None]
    return round(sum(bool(v) for v in vals) / len(vals), 4) if vals else None


def mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def group_value(row: dict, attr: str) -> str:
    return (row.get("persona") or {}).get(attr, "?")


def disaggregate(rows: list[dict], attr: str, metrics: dict[str, Metric], value_of=group_value) -> list[dict]:
    """One entry per attribute value (including values with n=0, so gaps stay visible)."""
    values = ATTRIBUTES[attr]["values"]
    buckets: dict[str, list[dict]] = {v: [] for v in values}
    for r in rows:
        buckets.setdefault(value_of(r, attr), []).append(r)
    out = []
    for v, sub in buckets.items():
        entry = {"value": v, "label": values.get(v, v), "n": len(sub)}
        for name, fn in metrics.items():
            entry[name] = fn(sub) if sub else None
        out.append(entry)
    return out


def gap(groups: list[dict], metric: str, min_n: int = 1) -> dict:
    vals = [(g[metric], g) for g in groups if g.get(metric) is not None and g["n"] >= min_n]
    if len(vals) < 2:
        return {"gap": None, "best": None, "worst": None}
    best = max(vals, key=lambda t: t[0])
    worst = min(vals, key=lambda t: t[0])
    return {"gap": round(best[0] - worst[0], 4), "best": best[1]["label"], "worst": worst[1]["label"], "worst_value": worst[0]}
