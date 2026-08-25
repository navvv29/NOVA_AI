"""
Always-on mode — background scheduler + SSE notification hub.

The scheduler periodically checks:
  1. Flashcards due for review
  2. Upcoming deadlines (todos)
  3. Study streak maintenance
  4. Learning milestones
  5. Career/academic goal progress

Notifications are pushed to connected clients via Server-Sent Events.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import AsyncGenerator

from ..analytics.queries import get_streak, get_weak_topics
from ..analytics.bandit import thompson_select


# ── SSE Hub ─────────────────────────────────────────────────────

class NotificationHub:
    """Manages SSE connections and broadcasts notifications."""

    def __init__(self):
        self._clients: list[asyncio.Queue] = []
        self._history: list[dict] = []
        self._max_history = 50

    async def subscribe(self) -> AsyncGenerator[dict, None]:
        """Yield notifications as they arrive. One SSE connection = one client."""
        queue: asyncio.Queue = asyncio.Queue()
        self._clients.append(queue)
        try:
            # Send recent history on connect
            for msg in self._history[-10:]:
                yield msg
            # Then stream live
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                    yield msg
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield {"type": "ping", "ts": time.time()}
        finally:
            self._clients.remove(queue)

    def broadcast(self, notification: dict):
        """Send a notification to all connected clients."""
        notification["ts"] = time.time()
        self._history.append(notification)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        for queue in self._clients:
            try:
                queue.put_nowait(notification)
            except asyncio.QueueFull:
                pass

    @property
    def client_count(self) -> int:
        return len(self._clients)


# Global hub instance
hub = NotificationHub()


# ── Scheduler ───────────────────────────────────────────────────

# User-configurable settings (stored in memory, persisted via the settings tool)
_user_settings = {
    "always_on": False,
    "voice_lock_enabled": False,
    "voice_passphrase": "",
    "authorized_voices": [],  # list of voice fingerprint hashes
    "pin_code": "",
    "reminder_interval_min": 30,
    "quiet_hours_start": 23,  # 11 PM
    "quiet_hours_end": 7,     # 7 AM
    "tts_enabled": False,
    "preferred_name": "",
    "learning_style": {},  # populated by the profiler
}


def get_settings() -> dict:
    return dict(_user_settings)


def update_settings(updates: dict):
    _user_settings.update(updates)


def _is_quiet_hours() -> bool:
    hour = datetime.now().hour
    start = _user_settings["quiet_hours_start"]
    end = _user_settings["quiet_hours_end"]
    if start > end:  # spans midnight
        return hour >= start or hour < end
    return start <= hour < end


async def _check_flashcards():
    """Check for due flashcards and notify."""
    try:
        from ..analytics.db import get_db
        with get_db() as db:
            now = datetime.now().isoformat()
            # Check flashcards.json for due cards
            import json
            from pathlib import Path
            flashcard_file = Path("nova_flashcards.json")
            if not flashcard_file.exists():
                return
            cards = json.loads(flashcard_file.read_text(encoding="utf-8"))
            due = [c for c in cards if c.get("next_review", "") <= datetime.now().isoformat()]
            if due:
                hub.broadcast({
                    "type": "flashcards_due",
                    "title": "🃏 Flashcard Review Ready",
                    "message": f"{len(due)} card(s) due for review. Tap to start!",
                    "action": "review_flashcards",
                    "count": len(due),
                })
    except Exception:
        pass


async def _check_deadlines():
    """Check for upcoming todo deadlines."""
    try:
        import json
        from pathlib import Path
        todo_file = Path("nova_todos.json")
        if not todo_file.exists():
            return
        todos = json.loads(todo_file.read_text(encoding="utf-8"))
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        overdue = [t for t in todos if not t.get("completed") and t.get("due_date") and t["due_date"] < today]
        due_today = [t for t in todos if not t.get("completed") and t.get("due_date") == today]
        due_tomorrow = [t for t in todos if not t.get("completed") and t.get("due_date") == tomorrow]

        if overdue:
            hub.broadcast({
                "type": "deadline_overdue",
                "title": "🔴 Overdue Tasks",
                "message": f"{len(overdue)} task(s) past their deadline!",
                "action": "show_todos",
                "tasks": [t["task"] for t in overdue[:3]],
            })
        if due_today:
            hub.broadcast({
                "type": "deadline_today",
                "title": "📋 Due Today",
                "message": f"{len(due_today)} task(s) due today",
                "action": "show_todos",
                "tasks": [t["task"] for t in due_today[:3]],
            })
    except Exception:
        pass


async def _check_streak():
    """Remind to study if streak might break."""
    try:
        streak = get_streak()
        if streak["current_streak"] > 0:
            # Check if they've studied today
            from ..analytics.db import get_db
            with get_db() as db:
                today = datetime.now().strftime("%Y-%m-%d")
                row = db.execute(
                    "SELECT COUNT(*) as cnt FROM ("
                    "  SELECT created_at FROM study_sessions WHERE DATE(created_at) = ?"
                    "  UNION ALL SELECT created_at FROM quiz_attempts WHERE DATE(created_at) = ?"
                    "  UNION ALL SELECT created_at FROM flashcard_reviews WHERE DATE(created_at) = ?"
                    ")", (today, today, today)
                ).fetchone()
                if row["cnt"] == 0:
                    hour = datetime.now().hour
                    if hour >= 18:  # Evening reminder
                        hub.broadcast({
                            "type": "streak_reminder",
                            "title": f"🔥 Keep Your {streak['current_streak']}-Day Streak!",
                            "message": "You haven't studied yet today. A quick 10-min session keeps the streak alive!",
                            "action": "study_now",
                        })
    except Exception:
        pass


async def _check_weak_topics():
    """Suggest reviewing weak topics."""
    try:
        weak = get_weak_topics(3)
        for w in weak:
            if w["avg_score"] < 60:
                hub.broadcast({
                    "type": "weak_topic",
                    "title": f"⚠️ {w['topic']} Needs Review",
                    "message": f"Your avg score is {w['avg_score']}%. A quick review could help!",
                    "action": "review_topic",
                    "topic": w["topic"],
                })
                break  # Only one at a time
    except Exception:
        pass


async def _check_bandit_suggestion():
    """Periodically suggest a study method based on the bandit."""
    try:
        top = thompson_select(n=1)
        if top:
            method = top[0]["method"].replace("_", " ").title()
            hub.broadcast({
                "type": "method_suggestion",
                "title": "🎯 Study Tip",
                "message": f"Based on your data, try '{method}' for your next session — it's your most effective method!",
                "action": "get_recommendation",
            })
    except Exception:
        pass


# ── Main Scheduler Loop ────────────────────────────────────────

_scheduler_running = False
_scheduler_task = None


async def scheduler_loop():
    """Background loop that runs checks periodically."""
    global _scheduler_running
    _scheduler_running = True

    check_interval = _user_settings["reminder_interval_min"] * 60  # seconds
    last_checks = {
        "flashcards": 0,
        "deadlines": 0,
        "streak": 0,
        "weak": 0,
        "bandit": 0,
    }

    while _scheduler_running:
        if not _user_settings["always_on"] or _is_quiet_hours():
            await asyncio.sleep(60)
            continue

        now = time.time()

        # Flashcard check — every 30 min
        if now - last_checks["flashcards"] > 1800:
            await _check_flashcards()
            last_checks["flashcards"] = now

        # Deadline check — every 6 hours
        if now - last_checks["deadlines"] > 21600:
            await _check_deadlines()
            last_checks["deadlines"] = now

        # Streak check — every hour
        if now - last_checks["streak"] > 3600:
            await _check_streak()
            last_checks["streak"] = now

        # Weak topics — every 12 hours
        if now - last_checks["weak"] > 43200:
            await _check_weak_topics()
            last_checks["weak"] = now

        # Bandit suggestion — every 4 hours
        if now - last_checks["bandit"] > 14400:
            await _check_bandit_suggestion()
            last_checks["bandit"] = now

        await asyncio.sleep(60)


def start_scheduler():
    """Start the background scheduler (call from FastAPI startup)."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(scheduler_loop())


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler_running, _scheduler_task
    _scheduler_running = False
    if _scheduler_task:
        _scheduler_task.cancel()
