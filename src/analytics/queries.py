"""
Analytics queries — read-only helpers that power the dashboard
and the adaptive recommender.
"""

from datetime import datetime, timedelta

from .db import get_db


# ── Study Sessions ──────────────────────────────────────────────

def record_session(topic: str, method: str, duration_min: float,
                   score_before: float = None, score_after: float = None,
                   confidence: float = 0.5, notes: str = "") -> int:
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO study_sessions (topic, method, duration_min, "
            "score_before, score_after, confidence, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (topic, method, duration_min, score_before, score_after,
             confidence, notes),
        )
        return cur.lastrowid


# ── Quiz Attempts ───────────────────────────────────────────────

def record_quiz(topic: str, score: float, total: int,
                difficulty: str = "medium", method: str = "general",
                time_spent: float = 0) -> int:
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO quiz_attempts (topic, difficulty, score, total, "
            "method, time_spent) VALUES (?, ?, ?, ?, ?, ?)",
            (topic, difficulty, score, total, method, time_spent),
        )
        return cur.lastrowid


# ── Flashcard Reviews ───────────────────────────────────────────

def record_flashcard_review(card_id: int, topic: str, rating: str,
                             ease_factor: float, interval_days: float,
                             time_taken: float = 0) -> int:
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO flashcard_reviews (card_id, topic, rating, "
            "ease_factor, interval_days, time_taken) VALUES (?, ?, ?, ?, ?, ?)",
            (card_id, topic, rating, ease_factor, interval_days, time_taken),
        )
        return cur.lastrowid


# ── Method Rewards (for bandit) ────────────────────────────────

def record_method_reward(method: str, reward: float, topic: str = "general"):
    with get_db() as db:
        db.execute(
            "INSERT INTO method_rewards (method, reward, topic) VALUES (?, ?, ?)",
            (method, reward, topic),
        )


def get_method_rewards(method: str = None, topic: str = None,
                        days: int = 30) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    query = "SELECT method, reward, topic, created_at FROM method_rewards WHERE created_at >= ?"
    params = [since]
    if method:
        query += " AND method = ?"
        params.append(method)
    if topic:
        query += " AND topic = ?"
        params.append(topic)
    with get_db() as db:
        rows = db.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ── Dashboard Aggregates ────────────────────────────────────────

def get_overview_stats(days: int = 30) -> dict:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_db() as db:
        sessions = db.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(duration_min),0) as total_min "
            "FROM study_sessions WHERE created_at >= ?", (since,)
        ).fetchone()
        quizzes = db.execute(
            "SELECT COUNT(*) as cnt, COALESCE(AVG(CASE WHEN total>0 THEN score*1.0/total END),0) as avg_score "
            "FROM quiz_attempts WHERE created_at >= ?", (since,)
        ).fetchone()
        reviews = db.execute(
            "SELECT COUNT(*) as cnt FROM flashcard_reviews WHERE created_at >= ?", (since,)
        ).fetchone()
        topics = db.execute(
            "SELECT DISTINCT topic FROM study_sessions WHERE created_at >= ? "
            "UNION SELECT DISTINCT topic FROM quiz_attempts WHERE created_at >= ? "
            "UNION SELECT DISTINCT topic FROM flashcard_reviews WHERE created_at >= ?",
            (since, since, since),
        ).fetchall()

        return {
            "total_sessions": sessions["cnt"],
            "total_study_minutes": round(sessions["total_min"], 1),
            "total_quizzes": quizzes["cnt"],
            "avg_quiz_score": round(quizzes["avg_score"] * 100, 1),
            "total_flashcard_reviews": reviews["cnt"],
            "topics_studied": [t["topic"] for t in topics],
            "period_days": days,
        }


def get_topic_breakdown(days: int = 30) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_db() as db:
        rows = db.execute("""
            SELECT topic, COUNT(*) as sessions, COALESCE(SUM(duration_min),0) as minutes
            FROM study_sessions WHERE created_at >= ?
            GROUP BY topic ORDER BY minutes DESC
        """, (since,)).fetchall()
        return [dict(r) for r in rows]


def get_method_effectiveness(days: int = 30) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_db() as db:
        rows = db.execute("""
            SELECT method,
                   COUNT(*) as uses,
                   ROUND(AVG(reward), 3) as avg_reward,
                   ROUND(MIN(reward), 3) as min_reward,
                   ROUND(MAX(reward), 3) as max_reward
            FROM method_rewards WHERE created_at >= ?
            GROUP BY method ORDER BY avg_reward DESC
        """, (since,)).fetchall()
        return [dict(r) for r in rows]


def get_progress_over_time(days: int = 30) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_db() as db:
        rows = db.execute("""
            SELECT DATE(created_at) as day,
                   COUNT(*) as quizzes,
                   ROUND(AVG(CASE WHEN total>0 THEN score*1.0/total END)*100, 1) as avg_score
            FROM quiz_attempts WHERE created_at >= ?
            GROUP BY day ORDER BY day
        """, (since,)).fetchall()
        return [dict(r) for r in rows]


def get_streak() -> dict:
    with get_db() as db:
        rows = db.execute("""
            SELECT DISTINCT DATE(created_at) as day FROM (
                SELECT created_at FROM study_sessions
                UNION ALL
                SELECT created_at FROM quiz_attempts
                UNION ALL
                SELECT created_at FROM flashcard_reviews
            ) ORDER BY day DESC
        """).fetchall()
    if not rows:
        return {"current_streak": 0, "longest_streak": 0}

    days = [r["day"] for r in rows]
    streak = 1
    longest = 1
    today = datetime.now().date()

    for i in range(1, len(days)):
        d1 = datetime.strptime(days[i - 1], "%Y-%m-%d").date()
        d2 = datetime.strptime(days[i], "%Y-%m-%d").date()
        if (d1 - d2).days == 1:
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 1

    # Check if streak is current (includes today or yesterday)
    latest = datetime.strptime(days[0], "%Y-%m-%d").date()
    if (today - latest).days > 1:
        streak = 0

    return {"current_streak": streak, "longest_streak": longest}


def get_weak_topics(top_n: int = 5) -> list[dict]:
    """Topics with lowest average quiz scores — prime candidates for review."""
    with get_db() as db:
        rows = db.execute("""
            SELECT topic,
                   COUNT(*) as attempts,
                   ROUND(AVG(CASE WHEN total>0 THEN score*1.0/total END)*100, 1) as avg_score
            FROM quiz_attempts
            GROUP BY topic
            HAVING attempts >= 1
            ORDER BY avg_score ASC
            LIMIT ?
        """, (top_n,)).fetchall()
        return [dict(r) for r in rows]
