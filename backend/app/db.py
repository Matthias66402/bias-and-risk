"""Thin sqlite3 wrapper (stdlib only). JSON columns are (de)serialized transparently."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'chat',          -- chat | eval
    eval_run_id TEXT,
    message TEXT NOT NULL,                         -- original customer text
    message_sent TEXT NOT NULL,                    -- text after redaction (what the LLM saw)
    persona TEXT NOT NULL,                         -- JSON, monitoring only
    profile_sent TEXT NOT NULL,                    -- JSON, attributes actually sent to LLM
    blinding INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    answer TEXT NOT NULL,
    rec_type TEXT NOT NULL,
    rec_confidence REAL NOT NULL,
    rec_rationale TEXT NOT NULL,
    sources TEXT NOT NULL,                         -- JSON list
    top_score REAL NOT NULL,
    low_retrieval INTEGER NOT NULL,
    routed INTEGER NOT NULL,
    route_reason TEXT NOT NULL,
    is_holdout INTEGER NOT NULL DEFAULT 0,
    proxy_warnings TEXT NOT NULL                   -- JSON list
);
CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interaction_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',        -- pending | decided
    decided_at TEXT,
    final_type TEXT,
    accepted INTEGER,
    rationale TEXT,
    reviewer TEXT,
    review_seconds REAL
);
CREATE TABLE IF NOT EXISTS labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interaction_id TEXT NOT NULL,
    annotator TEXT NOT NULL,
    rubric_version TEXT NOT NULL,
    scores TEXT NOT NULL,                          -- JSON {criterion: int}
    comment TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(interaction_id, annotator, rubric_version)
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interaction_id TEXT NOT NULL,
    helpful INTEGER NOT NULL,
    resolved INTEGER,
    comment TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kb_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    interaction_id TEXT,
    reason TEXT NOT NULL,
    question TEXT NOT NULL,
    topic TEXT,
    status TEXT NOT NULL DEFAULT 'pending',        -- pending | approved | rejected
    reviewer TEXT,
    text TEXT,
    decided_at TEXT
);
CREATE TABLE IF NOT EXISTS eval_runs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,                          -- running | done | failed
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    blinding INTEGER NOT NULL,
    use_judge INTEGER NOT NULL,
    total INTEGER NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    config TEXT NOT NULL,
    summary TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS eval_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    axis TEXT NOT NULL,                            -- reference | <attribute>
    value TEXT NOT NULL,
    interaction_id TEXT,
    rec_type TEXT NOT NULL,
    expected TEXT NOT NULL,                        -- JSON list
    correct INTEGER NOT NULL,
    judge_score REAL,
    answer_len INTEGER NOT NULL,
    error TEXT
);
"""

JSON_COLS = {"persona", "profile_sent", "sources", "proxy_warnings", "scores", "config", "summary", "expected"}


def _encode(v: Any) -> Any:
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return int(v)
    return v


def _decode(row: sqlite3.Row) -> dict:
    d = dict(row)
    for k in JSON_COLS & d.keys():
        if isinstance(d[k], str):
            d[k] = json.loads(d[k])
    return d


class Database:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def execute(self, sql: str, params: tuple | list = ()) -> int:
        with self._lock:
            cur = self._conn.execute(sql, [_encode(p) for p in params])
            self._conn.commit()
            return cur.lastrowid

    def query(self, sql: str, params: tuple | list = ()) -> list[dict]:
        with self._lock:
            return [_decode(r) for r in self._conn.execute(sql, [_encode(p) for p in params]).fetchall()]

    def one(self, sql: str, params: tuple | list = ()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def insert(self, table: str, data: dict) -> int:
        cols = ", ".join(data)
        marks = ", ".join("?" for _ in data)
        return self.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(data.values()))

    def update(self, table: str, key: str, key_value: Any, data: dict) -> None:
        sets = ", ".join(f"{k} = ?" for k in data)
        self.execute(f"UPDATE {table} SET {sets} WHERE {key} = ?", [*data.values(), key_value])
