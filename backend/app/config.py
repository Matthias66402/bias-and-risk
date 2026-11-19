"""Static configuration (from .env) and mutable runtime settings (persisted as JSON)."""
from __future__ import annotations

import json
import threading
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_DIR / ".env", extra="ignore")

    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""

    openai_chat_model: str = "gpt-4.1-mini"
    groq_chat_model: str = "openai/gpt-oss-120b"
    gemini_chat_model: str = "gemini-2.5-flash"

    # "openai" (needs OPENAI_API_KEY) or "hash" (offline bag-of-words fallback)
    embedding_backend: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    storage_dir: Path = BACKEND_DIR / "storage"
    kb_dir: Path = DATA_DIR / "kb"
    frontend_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


class RuntimeSettings(BaseModel):
    """Values the UI may change at runtime (Settings page)."""

    default_provider: str = "openai"
    judge_provider: str | None = Field(None, description="Provider für LLM-Judge; None = default_provider")
    top_k: int = Field(5, ge=1, le=10)
    low_retrieval_threshold: float = Field(0.3, ge=0, le=1, description="Ähnlichkeit unter diesem Wert gilt als KB-Lücke")
    confidence_threshold: float = Field(0.7, ge=0, le=1, description="Darunter -> Mensch entscheidet")
    holdout_rate: float = Field(0.1, ge=0, le=1, description="Zufallsanteil, der immer an Menschen geht")
    fairness_gap_threshold: float = Field(0.15, ge=0, le=1, description="Max. erlaubte Lücke zwischen Gruppen")
    min_group_share: float = Field(0.05, ge=0, le=1, description="Gruppen darunter gelten als unterrepräsentiert")


class RuntimeSettingsStore:
    def __init__(self, path: Path | None):
        self._path = path
        self._lock = threading.Lock()
        self._value = RuntimeSettings()
        if path and path.exists():
            self._value = RuntimeSettings.model_validate_json(path.read_text(encoding="utf-8"))

    def get(self) -> RuntimeSettings:
        return self._value

    def update(self, new: RuntimeSettings) -> RuntimeSettings:
        with self._lock:
            self._value = new
            if self._path:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._path.write_text(json.dumps(new.model_dump(), indent=2), encoding="utf-8")
        return self._value
