"""Service container – one place to wire dependencies (swapped out in tests)."""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.config import DATA_DIR, RuntimeSettingsStore, Settings
from app.db import Database
from app.llm.providers import ProviderRegistry
from app.rag.embeddings import Embedder, HashEmbedder, OpenAIEmbedder
from app.rag.store import VectorStore

log = logging.getLogger(__name__)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@dataclass
class Services:
    db: Database
    store: VectorStore
    providers: ProviderRegistry
    runtime: RuntimeSettingsStore
    kb_dir: Path
    goal: dict = field(default_factory=lambda: load_yaml(DATA_DIR / "goal_config.yaml"))
    rubric: dict = field(default_factory=lambda: load_yaml(DATA_DIR / "rubric_v1.yaml"))
    eval_set: dict = field(default_factory=lambda: load_yaml(DATA_DIR / "eval" / "questions.yaml"))
    rng: random.Random = field(default_factory=random.Random)


def build_embedder(s: Settings) -> Embedder:
    if s.embedding_backend == "openai" and s.openai_api_key:
        return OpenAIEmbedder(s.openai_api_key, s.embedding_model)
    log.warning("Nutze HashEmbedder (offline) – Retrieval-Qualität eingeschränkt.")
    return HashEmbedder()


def build_default_services(s: Settings | None = None) -> Services:
    import chromadb

    s = s or Settings()
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    embedder = build_embedder(s)
    # separate collection per embedder, so switching backends never mixes vector spaces
    collection = "shop_kb_" + embedder.name.replace(":", "_").replace("-", "_")
    store = VectorStore(chromadb.PersistentClient(path=str(s.storage_dir / "chroma")), embedder, collection)
    return Services(
        db=Database(s.storage_dir / "app.db"),
        store=store,
        providers=ProviderRegistry.from_settings(s),
        runtime=RuntimeSettingsStore(s.storage_dir / "runtime_settings.json"),
        kb_dir=s.kb_dir,
    )


_services: Services | None = None


def get_services() -> Services:
    if _services is None:
        raise RuntimeError("Services not initialised")
    return _services


def set_services(svc: Services) -> None:
    global _services
    _services = svc
