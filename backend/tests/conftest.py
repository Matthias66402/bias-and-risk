import random
import re
import shutil
import uuid

import chromadb
import pytest
from fastapi.testclient import TestClient

from app.config import DATA_DIR, RuntimeSettings, RuntimeSettingsStore
from app.db import Database
from app.llm.providers import ProviderRegistry
from app.main import create_app
from app.rag.embeddings import HashEmbedder
from app.rag.ingest import load_kb
from app.rag.store import VectorStore
from app.services import Services


class FakeProvider:
    """Deterministic stand-in for an LLM. With biased=True it discriminates on
    the name 'Mehmet' and on age 65+, which the counterfactual eval must detect."""

    def __init__(self, biased: bool = False, name: str = "fake"):
        self.name, self.model, self.biased = name, "fake-1", biased
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append((system, user))
        if "POLICY-KONFORME" in user:  # judge
            return {"score": 4, "reason": "ok"}
        query = user.split("KUNDENANFRAGE:")[-1]
        ids = re.findall(r"^\[([^\]]+)\]", user, flags=re.M)
        if self.biased and ("Mehmet" in user or "65+" in user):
            rec = ("deny", 0.9, "Aufgrund von Alter bzw. Herkunft keine Kulanz.")
        elif "90" in query:
            rec = ("deny", 0.9, "Frist um mehr als 14 Tage überschritten.")
        elif "38" in query:
            rec = ("goodwill", 0.8, "Frist um weniger als 14 Tage überschritten, Ware unbenutzt.")
        elif "Zahnbürst" in query or "toothbrush" in query:
            rec = ("deny", 0.9, "Geöffnete Hygieneartikel sind ausgeschlossen.")
        elif "Rücksendung ist" in query or "Mein Paket ist bei Ihnen" in query or "retoure is" in query or "My return" in query:
            rec = ("info", 0.9, "Erstattung binnen 5 Werktagen.")
        elif "Paket" in query or "Kaffee" in query or "Kopfhörer" in query or "order" in query or "coffee" in query or "headphones" in query or "paket" in query or "kaffe" in query or "kopfhörer" in query:
            rec = ("replacement", 0.9, "Ersatz laut Versand-/Gewährleistungsrichtlinie.")
        else:
            rec = ("refund", 0.9, "Innerhalb der 30-Tage-Frist.")
        return {
            "answer": f"Antwort auf: {query.strip()[:40]}",
            "recommendation": {"type": rec[0], "confidence": rec[1], "rationale": rec[2]},
            "cited_sources": ids[:2],
        }


def make_services(tmp_path, biased: bool = False) -> Services:
    kb_dir = tmp_path / "kb"
    shutil.copytree(DATA_DIR / "kb", kb_dir)
    store = VectorStore(chromadb.EphemeralClient(), HashEmbedder(), f"test_{uuid.uuid4().hex[:8]}")
    store.rebuild(load_kb(kb_dir))
    reg = ProviderRegistry()
    fake = FakeProvider(biased=biased)
    reg.register("fake", "fake-1", lambda: fake)
    runtime = RuntimeSettingsStore(None)
    runtime.update(RuntimeSettings(default_provider="fake", holdout_rate=0.0, low_retrieval_threshold=0.05))
    return Services(db=Database(":memory:"), store=store, providers=reg, runtime=runtime, kb_dir=kb_dir, rng=random.Random(0))


@pytest.fixture
def svc(tmp_path):
    return make_services(tmp_path)


@pytest.fixture
def biased_svc(tmp_path):
    return make_services(tmp_path, biased=True)


@pytest.fixture
def client(svc):
    with TestClient(create_app(svc)) as c:
        yield c
