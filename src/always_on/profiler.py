"""
Learning Style Profiler — analyzes study behavior to understand HOW
the user learns best, not just WHAT they struggle with.

Tracks:
  - Preferred study times (morning vs evening)
  - Preferred method per topic
  - Response to difficulty (does harder = more engagement or frustration?)
  - Session length sweet spot
  - Visual vs text preference (from method usage patterns)
  - Teaching style preference (examples-first vs theory-first)
"""

import json
from datetime import datetime
from pathlib import Path

from ..analytics.db import get_db
from ..analytics.queries import get_method_effectiveness, get_topic_breakdown

PROFILE_FILE = Path("nova_learning_profile.json")

# Learning style categories
VISUAL_METHODS = {"mind_mapping", "flashcards"}
TEXT_METHODS = {"cornell_notes", "summarize_text", "elaboration"}
ACTIVE_METHODS = {"active_recall", "practice_problems", "retrieval_practice", "quiz"}
COLLABORATIVE_METHODS = {"teach_back", "interleaving"}
FOCUSED_METHODS = {"pomodoro", "flashcards"}


def _load_profile() -> dict:
    if PROFILE_FILE.exists():
        try:
            return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "visual_score": 0.5,
        "text_score": 0.5,
        "active_score": 0.5,
        "collaborative_score": 0.5,
        "focused_score": 0.5,
        "preferred_time": "unknown",
        "preferred_session_length_min": 30,
        "teaching_style": "adaptive",  # adaptive, example-first, theory-first, socratic
        "frustration_threshold": 0.4,  # quiz score below this = frustrated
        "engagement_peak": 0.7,  # quiz score around this = most engaged
        "updated_at": datetime.now().isoformat(),
        "data_points": 0,
    }


def _save_profile(profile: dict):
    profile["updated_at"] = datetime.now().isoformat()
    PROFILE_FILE.write_text(json.dumps(profile, indent=2), encoding="utf-8")


def analyze_learning_style() -> dict:
    """Rebuild the learning profile from all available data."""
    profile = _load_profile()

    # Get method effectiveness
    methods = get_method_effectiveness(days=90)
    if not methods:
        return profile

    method_scores = {m["method"]: m["avg_reward"] for m in methods}
    total_uses = sum(m["uses"] for m in methods)

    if total_uses < 3:
        profile["data_points"] = total_uses
        _save_profile(profile)
        return profile

    # Visual vs Text preference
    visual_avg = sum(method_scores.get(m, 0.5) for m in VISUAL_METHODS) / max(len(VISUAL_METHODS), 1)
    text_avg = sum(method_scores.get(m, 0.5) for m in TEXT_METHODS) / max(len(TEXT_METHODS), 1)
    v_total = visual_avg + text_avg or 1
    profile["visual_score"] = round(visual_avg / v_total, 3)
    profile["text_score"] = round(text_avg / v_total, 3)

    # Active vs Passive
    active_avg = sum(method_scores.get(m, 0.5) for m in ACTIVE_METHODS) / max(len(ACTIVE_METHODS), 1)
    collab_avg = sum(method_scores.get(m, 0.5) for m in COLLABORATIVE_METHODS) / max(len(COLLABORATIVE_METHODS), 1)
    focused_avg = sum(method_scores.get(m, 0.5) for m in FOCUSED_METHODS) / max(len(FOCUSED_METHODS), 1)

    profile["active_score"] = round(active_avg, 3)
    profile["collaborative_score"] = round(collab_avg, 3)
    profile["focused_score"] = round(focused_avg, 3)

    # Preferred study time from session data
    with get_db() as db:
        rows = db.execute("""
            SELECT strftime('%H', created_at) as hour, COUNT(*) as cnt
            FROM study_sessions
            GROUP BY hour ORDER BY cnt DESC LIMIT 1
        """).fetchall()
        if rows:
            h = int(rows[0]["hour"])
            if 5 <= h < 12:
                profile["preferred_time"] = "morning"
            elif 12 <= h < 17:
                profile["preferred_time"] = "afternoon"
            elif 17 <= h < 22:
                profile["preferred_time"] = "evening"
            else:
                profile["preferred_time"] = "night"

        # Average session length
        row = db.execute(
            "SELECT AVG(duration_min) as avg_len FROM study_sessions WHERE duration_min > 0"
        ).fetchone()
        if row["avg_len"]:
            profile["preferred_session_length_min"] = round(row["avg_len"])

        # Data points count
        row = db.execute("SELECT COUNT(*) as cnt FROM study_sessions").fetchone()
        profile["data_points"] = row["cnt"]

    # Determine teaching style
    if profile["active_score"] > 0.65:
        profile["teaching_style"] = "socratic"  # question-driven
    elif profile["visual_score"] > 0.6:
        profile["teaching_style"] = "example-first"
    elif profile["text_score"] > 0.6:
        profile["teaching_style"] = "theory-first"
    else:
        profile["teaching_style"] = "adaptive"

    _save_profile(profile)
    return profile


def get_teaching_instructions() -> str:
    """Generate teaching style instructions for the agent system prompt."""
    profile = analyze_learning_style()

    instructions = []

    # Teaching style
    style = profile.get("teaching_style", "adaptive")
    if style == "socratic":
        instructions.append(
            "Use Socratic questioning — ask the user guiding questions instead of "
            "giving direct answers. Help them discover concepts through reasoning."
        )
    elif style == "example-first":
        instructions.append(
            "Lead with concrete examples and visual diagrams before theory. "
            "Use analogies and visual metaphors to explain concepts."
        )
    elif style == "theory-first":
        instructions.append(
            "Start with clear definitions and theoretical frameworks, then "
            "reinforce with examples. The user learns well from structured explanations."
        )
    else:
        instructions.append(
            "Adapt your teaching style — use examples for concrete topics, "
            "theory for abstract ones, and questions to check understanding."
        )

    # Time preference
    pref_time = profile.get("preferred_time", "unknown")
    if pref_time != "unknown":
        instructions.append(
            f"The user studies best in the {pref_time}. "
            f"Suggest study sessions during this time for optimal results."
        )

    # Session length
    length = profile.get("preferred_session_length_min", 30)
    instructions.append(
        f"Optimal study session length: ~{length} minutes. "
        f"Suggest focused blocks of this duration."
    )

    # Visual/active preference
    if profile.get("visual_score", 0.5) > 0.6:
        instructions.append(
            "This user is a visual learner. Use emoji diagrams, ASCII art, "
            "tables, and structured formatting to convey information."
        )
    if profile.get("active_score", 0.5) > 0.65:
        instructions.append(
            "This user learns best through active practice. Prioritize quizzes, "
            "exercises, and self-testing over passive reading."
        )

    return "\n".join(instructions) if instructions else ""


def get_profile_summary() -> str:
    """Human-readable summary of the learning profile."""
    profile = analyze_learning_style()

    lines = [
        "🧠 **Your Learning Profile:**\n",
        f"**Teaching style:** {profile['teaching_style'].replace('_', ' ').title()}",
        f"**Preferred study time:** {profile['preferred_time'].title()}",
        f"**Optimal session length:** {profile['preferred_session_length_min']} min",
        f"**Data points:** {profile['data_points']} sessions\n",
        "**Learning dimensions:**",
    ]

    dims = [
        ("Visual", profile["visual_score"]),
        ("Text", profile["text_score"]),
        ("Active Practice", profile["active_score"]),
        ("Collaborative", profile["collaborative_score"]),
        ("Focused", profile["focused_score"]),
    ]

    for name, score in dims:
        bar_len = int(score * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        lines.append(f"  {name:20s} {bar} {score:.0%}")

    if profile["data_points"] < 5:
        lines.append(
            "\n💡 Keep studying and tracking! I need more data to refine "
            "your profile. The more you use me, the better I adapt."
        )

    return "\n".join(lines)
