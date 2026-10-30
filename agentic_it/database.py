from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import DATABASE_PATH


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            session_id TEXT PRIMARY KEY, facts TEXT NOT NULL DEFAULT '[]', updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
            user_text TEXT NOT NULL, assistant_text TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT NOT NULL, category TEXT NOT NULL, priority TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
            event_type TEXT NOT NULL, summary TEXT NOT NULL, details TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)


def get_memory(session_id: str) -> list[str]:
    with _connect() as conn:
        row = conn.execute("SELECT facts FROM memories WHERE session_id=?", (session_id,)).fetchone()
    return json.loads(row["facts"]) if row else []


def add_memory(session_id: str, fact: str) -> None:
    fact = fact.strip()[:240]
    if not fact:
        return
    facts = get_memory(session_id)
    if fact.lower() not in [item.lower() for item in facts]:
        facts = (facts + [fact])[-12:]
    with _connect() as conn:
        conn.execute("""INSERT INTO memories(session_id,facts,updated_at) VALUES(?,?,?)
        ON CONFLICT(session_id) DO UPDATE SET facts=excluded.facts,updated_at=excluded.updated_at""",
                     (session_id, json.dumps(facts, ensure_ascii=False), _now()))


def save_conversation(session_id: str, user_text: str, assistant_text: str) -> None:
    with _connect() as conn:
        conn.execute("INSERT INTO conversations(session_id,user_text,assistant_text,created_at) VALUES(?,?,?,?)",
                     (session_id, user_text[:4000], assistant_text[:8000], _now()))


def recent_conversations(session_id: str, limit: int = 6) -> list[dict[str, str]]:
    with _connect() as conn:
        rows = conn.execute("SELECT user_text,assistant_text,created_at FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?",
                            (session_id, limit)).fetchall()
    return [dict(row) for row in reversed(rows)]


def log_event(session_id: str, event_type: str, summary: str, details: dict[str, Any] | None = None) -> None:
    with _connect() as conn:
        conn.execute("INSERT INTO audit_events(session_id,event_type,summary,details,created_at) VALUES(?,?,?,?,?)",
                     (session_id, event_type, summary[:300], json.dumps(details or {}, ensure_ascii=False)[:4000], _now()))


def list_events(limit: int = 100) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def create_ticket(session_id: str, title: str, description: str, category: str, priority: str) -> str:
    ticket_id = f"IT-{uuid4().hex[:8].upper()}"
    with _connect() as conn:
        conn.execute("INSERT INTO tickets VALUES(?,?,?,?,?,?,?,?)",
                     (ticket_id, session_id, title[:180], description[:3000], category,
                      priority, "Open", _now()))
    return ticket_id


def list_tickets(limit: int = 100) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def clear_session(session_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM memories WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM conversations WHERE session_id=?", (session_id,))

