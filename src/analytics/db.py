"""
Learning analytics database.

SQLite-backed store that tracks:
  - Study sessions (topic, method, duration, score before/after)
  - Quiz attempts (topic, difficulty, score, method used)
  - Flashcard reviews (card_id, topic, rating, time taken)
  - Method effectiveness (per-study-method reward history for bandit)

Schema is auto-created on first access.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = os.getenv("NOVA_ANALYTICS_DB", "nova_analytics.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                topic       TEXT NOT NULL,
                method      TEXT NOT NULL,
                duration_min REAL DEFAULT 0,
                score_before REAL,
                score_after  REAL,
                confidence   REAL DEFAULT 0.5,
                notes        TEXT,
                created_at   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                topic       TEXT NOT NULL,
                difficulty  TEXT DEFAULT 'medium',
                score       REAL NOT NULL,
                total       INTEGER NOT NULL,
                method      TEXT DEFAULT 'general',
                time_spent  REAL DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS flashcard_reviews (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id     INTEGER NOT NULL,
                topic       TEXT DEFAULT 'general',
                rating      TEXT NOT NULL,
                ease_factor REAL DEFAULT 2.5,
                interval_days REAL DEFAULT 1,
                time_taken  REAL DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS method_rewards (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                method      TEXT NOT NULL,
                reward      REAL NOT NULL,
                topic       TEXT DEFAULT 'general',
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS learning_goals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                topic       TEXT NOT NULL,
                target_score REAL DEFAULT 0.8,
                current_score REAL DEFAULT 0,
                streak      INTEGER DEFAULT 0,
                active      INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_topic ON study_sessions(topic);
            CREATE INDEX IF NOT EXISTS idx_sessions_method ON study_sessions(method);
            CREATE INDEX IF NOT EXISTS idx_quiz_topic ON quiz_attempts(topic);
            CREATE INDEX IF NOT EXISTS idx_flashcard_topic ON flashcard_reviews(topic);
            CREATE INDEX IF NOT EXISTS idx_rewards_method ON method_rewards(method);
        """)


# Auto-init on import
init_db()
