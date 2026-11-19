"""ChromaDB-backed vector store with externally computed embeddings."""
from __future__ import annotations

from app.models import Source
from app.rag.embeddings import Embedder
from app.rag.ingest import Chunk

COLLECTION = "shop_kb"


class VectorStore:
    def __init__(self, client, embedder: Embedder, collection: str = COLLECTION):
        self.client, self.embedder, self.collection_name = client, embedder, collection
        self._col = self._open()

    def _open(self):
        return self.client.get_or_create_collection(
            self.collection_name, metadata={"hnsw:space": "cosine"}, embedding_function=None
        )

    def rebuild(self, chunks: list[Chunk]) -> int:
        self.client.delete_collection(self.collection_name)
        self._col = self._open()
        if chunks:
            self._col.add(
                ids=[c.id for c in chunks],
                documents=[c.text for c in chunks],
                metadatas=[c.metadata for c in chunks],
                embeddings=self.embedder.embed([c.text for c in chunks]),
            )
        return len(chunks)

    def count(self) -> int:
        return self._col.count()

    def search(self, query: str, k: int) -> list[Source]:
        if self.count() == 0:
            return []
        res = self._col.query(
            query_embeddings=self.embedder.embed([query]),
            n_results=min(k, self.count()),
            include=["documents", "metadatas", "distances"],
        )
        out = []
        for cid, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]):
            out.append(Source(id=cid, title=meta.get("title", ""), topic=meta.get("topic", ""), score=round(1 - dist, 4), text=doc))
        return out

    def all_metadata(self) -> list[dict]:
        return self._col.get(include=["metadatas"])["metadatas"] or []
