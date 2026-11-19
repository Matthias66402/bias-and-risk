"""Load the Markdown knowledge base into chunks with coverage metadata.

Each KB file starts with YAML front matter, e.g.
---
title: Rücksendungen
topic: retouren
language: de          # de | en
readability: standard # standard | einfach
audience: alle        # alle | premium | ...
---
and is split into chunks at '## ' headings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


DEFAULT_META = {"topic": "sonstiges", "language": "de", "readability": "standard", "audience": "alle"}


def parse_front_matter(raw: str) -> tuple[dict, str]:
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        return yaml.safe_load(fm) or {}, body.strip()
    return {}, raw.strip()


def load_kb(kb_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(kb_dir.rglob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        doc_id = path.relative_to(kb_dir).with_suffix("").as_posix()
        title = str(meta.get("title", path.stem))
        base = {**DEFAULT_META, **{k: str(v) for k, v in meta.items()}, "doc": doc_id, "title": title}
        sections = [s.strip() for s in ("\n" + body).split("\n## ") if s.strip()]
        for i, section in enumerate(sections):
            heading, _, content = section.partition("\n")
            heading = heading.lstrip("# ").strip()
            text = f"{title} – {heading}\n{content.strip()}".strip()
            chunks.append(Chunk(id=f"{doc_id}#{i}", text=text, metadata={**base, "section": heading}))
    return chunks
