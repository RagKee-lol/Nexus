"""
SQLite persistence layer. Local file, no external service.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
import datetime as dt

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "nexus.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT,
    user_profile TEXT
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    stock TEXT,
    agent TEXT,
    signal TEXT,
    confidence REAL,
    latency_ms REAL
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    stock TEXT,
    user_profile TEXT,
    final_decision TEXT,
    confidence REAL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    user_profile TEXT,
    portfolio_risk_score REAL,
    portfolio_value REAL
);
"""


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def new_session(user_profile: str) -> str:
    session_id = str(uuid.uuid4())[:8]
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO sessions (session_id, started_at, user_profile) VALUES (?, ?, ?)",
            (session_id, dt.datetime.now().isoformat(), user_profile),
        )
        conn.commit()
    finally:
        conn.close()
    return session_id


def log_investigation(session_id: str, stock: str, user_profile: str, investigation) -> None:
    conn = _connect()
    try:
        ts = dt.datetime.now().isoformat()
        for agent_result in [investigation.technical, investigation.fundamental,
                              investigation.sentiment, investigation.risk, investigation.governance]:
            conn.execute(
                "INSERT INTO agent_runs (session_id, timestamp, stock, agent, signal, confidence, latency_ms) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, ts, stock, agent_result.agent, agent_result.signal,
                 agent_result.confidence, agent_result.latency_ms),
            )
        conn.execute(
            "INSERT INTO recommendations (session_id, timestamp, stock, user_profile, final_decision, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, ts, stock, user_profile, investigation.synthesis.final_signal, investigation.synthesis.confidence),
        )
        conn.commit()
    finally:
        conn.close()


def log_portfolio_snapshot(session_id: str, user_profile: str, portfolio: dict) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO portfolio_snapshots (session_id, timestamp, user_profile, portfolio_risk_score, portfolio_value) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, dt.datetime.now().isoformat(), user_profile,
             portfolio.get("portfolio_risk_score", 0), portfolio.get("portfolio_value", 0)),
        )
        conn.commit()
    finally:
        conn.close()


def get_session_stats(session_id: str) -> dict:
    conn = _connect()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM recommendations WHERE session_id=?", (session_id,))
        rec_count = cur.fetchone()[0]
        cur = conn.execute("SELECT AVG(latency_ms) FROM agent_runs WHERE session_id=?", (session_id,))
        avg_latency = cur.fetchone()[0] or 0.0
        return {"recommendation_count": rec_count, "avg_agent_latency_ms": round(avg_latency, 1)}
    finally:
        conn.close()
