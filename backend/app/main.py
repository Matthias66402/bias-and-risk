"""FastAPI entry point: `uvicorn app.main:app --reload` (from backend/)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.rag.ingest import load_kb
from app.routers import admin, chat, dashboard, eval, labeling, queue
from app.services import Services, build_default_services, set_services

logging.basicConfig(level=logging.INFO)


def create_app(services: Services | None = None) -> FastAPI:
    settings = Settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        svc = services or build_default_services(settings)
        set_services(svc)
        if svc.store.count() == 0:  # first start: build the index
            try:
                svc.store.rebuild(load_kb(svc.kb_dir))
            except Exception:
                logging.exception("Initiales Indexieren fehlgeschlagen – später über POST /api/admin/ingest wiederholen")
        yield

    app = FastAPI(
        title="Bias-aware RAG Support (Lumo Testshop)",
        description="Test-App: RAG-Kundensupport mit Bias-Abfederung über die 6 Phasen des ML-Lebenszyklus.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(CORSMiddleware, allow_origins=settings.frontend_origins, allow_methods=["*"], allow_headers=["*"])
    for r in (chat.router, queue.router, labeling.router, eval.router, dashboard.router, admin.router):
        app.include_router(r)

    @app.get("/api/health", tags=["admin"])
    def health() -> dict:
        return {"ok": True}

    return app


app = create_app()
