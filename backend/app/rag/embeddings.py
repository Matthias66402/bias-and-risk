"""Embedding backends: OpenAI (default) and a deterministic offline hash embedder."""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str):
        from openai import OpenAI

        self.client, self.model = OpenAI(api_key=api_key), model
        self.name = f"openai:{model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 64):
            resp = self.client.embeddings.create(model=self.model, input=texts[i : i + 64])
            out.extend(d.embedding for d in resp.data)
        return out


class HashEmbedder:
    """Bag-of-words hashed into a fixed vector. No semantics beyond word overlap,
    but fully offline and deterministic (used in tests and as a fallback)."""

    def __init__(self, dims: int = 512):
        self.dims = dims
        self.name = f"hash:{dims}"

    def _tokens(self, text: str) -> list[str]:
        words = re.findall(r"\w+", text.lower())
        # crude stemming so "Retoure"/"Retouren" overlap
        return [w[:6] for w in words if len(w) > 2]

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for t in texts:
            v = [0.0] * self.dims
            for tok in self._tokens(t):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                v[h % self.dims] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            vectors.append([x / norm for x in v])
        return vectors
