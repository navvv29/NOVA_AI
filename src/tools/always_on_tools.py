"""
Always-on mode tools — voice control, security, learning profiler,
career growth, and proactive notification management.
"""

import uuid
from langchain_core.tools import tool

from ..always_on.scheduler import get_settings, update_settings, hub
from ..always_on.security import (
    set_pin, remove_pin, get_security_status,
    list_voices, remove_voice, create_session, verify_session,
)
from ..always_on.profiler import (
    analyze_learning_style, get_teaching_instructions, get_profile_summary,
)
from ..always_on.growth import (
    add_skill, update_skill_xp, get_skills, add_milestone, get_milestones,
    set_academic_goal, get_academic_goals, set_career_goal, get_career_goals,
    get_growth_report, add_xp,
)
from ..analytics.queries import record_session


# ── Always-On Mode ──────────────────────────────────────────────

@tool
def set_always_on(enabled: bool = True) -> str:
    """Turn always-on mode on or off.

    When enabled, N.O.V.A proactively monitors your flashcards, deadlines,
    study streaks, and learning patterns — and notifies you when action is needed.
    """
    update_settings({"always_on": enabled})
    state = "🟢 ON" if enabled else "⚪ OFF"
    if enabled:
        hub.broadcast({
            "type": "system",
            "title": "🟢 Always-On Mode Enabled",
            "message": "I'm now actively monitoring your learning. I'll notify you when it's time to review!",
        })
    return f"Always-on mode: {state}\nI'll {'proactively help you stay on track' if enabled else 'only respond when you message me'}."


@tool
def get_always_on_status() -> str:
    """Check the current always-on mode status and settings."""
    settings = get_settings()
    lines = [
        f"🤖 **Always-On Status:** {'🟢 Active' if settings['always_on'] else '⚪ Inactive'}",
        f"  Reminder interval: every {settings['reminder_interval_min']} min",
        f"  Quiet hours: {settings['quiet_hours_start']}:00 - {settings['quiet_hours_end']}:00",
        f"  Connected clients: {hub.client_count}",
        f"  TTS: {'🟢 On' if settings['tts_enabled'] else '⚪ Off'}",
    ]
    if settings.get("preferred_name"):
        lines.append(f"  Preferred name: {settings['preferred_name']}")
    return "\n".join(lines)


@tool
def set_reminder_interval(minutes: int = 30) -> str:
    """Set how often the background scheduler checks for reminders.

    Parameters:
    - minutes: Check interval (15-120, default 30)
    """
    minutes = max(15, min(120, minutes))
    update_settings({"reminder_interval_min": minutes})
    return f"⏰ Reminder interval set to every {minutes} minutes."


@tool
def set_quiet_hours(start_hour: int = 23, end_hour: int = 7) -> str:
    """Set quiet hours when N.O.V.A won't send notifications.

    Parameters:
    - start_hour: When quiet hours begin (0-23, default 23 = 11 PM)
    - end_hour: When quiet hours end (0-23, default 7 = 7 AM)
    """
    update_settings({"quiet_hours_start": start_hour, "quiet_hours_end": end_hour})
    return f"🌙 Quiet hours: {start_hour}:00 - {end_hour}:00. No notifications during this time."


@tool
def set_preferred_name(name: str) -> str:
    """Set how N.O.V.A should address you."""
    update_settings({"preferred_name": name.strip()})
    return f"✅ I'll call you {name.strip()} from now on!"


# ── Voice & Security ────────────────────────────────────────────

@tool
def enable_voice_lock(enabled: bool = True) -> str:
    """Enable or disable voice lock security.

    When enabled, the agent only responds to authorized voices.
    Register voices first, then enable the lock.
    """
    from ..always_on.security import _load_security, _save_security
    sec = _load_security()
    sec["voice_lock_enabled"] = enabled
    _save_security(sec)
    if enabled and not sec["voice_fingerprints"]:
        return ("⚠️ Voice lock enabled, but no voices registered yet! "
                "Register at least one voice first using 'manage_voice'.")
    state = "🔒 ON" if enabled else "🔓 OFF"
    return f"Voice lock: {state}"


@tool
def manage_voice(action: str, label: str = "") -> str:
    """Manage authorized voices for voice lock.

    Actions:
    - 'list': Show all authorized voices
    - 'remove': Remove a voice by label
    - 'status': Show voice lock security status
    """
    action = action.lower().strip()
    if action == "list":
        return list_voices()
    elif action == "remove":
        if not label:
            return "Provide a voice label to remove."
        return remove_voice(label=label)
    elif action == "status":
        return get_security_status()
    else:
        return f"Unknown action '{action}'. Use: list, remove, or status."


@tool
def set_pin_code(pin: str = "") -> str:
    """Set or remove a backup PIN code for accessing the agent.

    Provide a 4-8 digit PIN to set it, or leave empty to remove.
    """
    if not pin:
        return remove_pin()
    return set_pin(pin)


@tool
def create_access_session(method: str = "text") -> str:
    """Create an authenticated session for accessing the agent.

    Parameters:
    - method: 'voice' or 'text' (how you're authenticating)
    """
    token = create_session(method)
    return f"🔑 Session created. Token: {token[:16]}... (valid for 8 hours)"


# ── Learning Profile ────────────────────────────────────────────

@tool
def get_learning_profile() -> str:
    """Get your personalized learning style profile.

    Shows your preferred methods, study times, teaching style,
    and other patterns the system has learned about you.
    """
    return get_profile_summary()


@tool
def update_learning_profile() -> str:
    """Force a refresh of your learning style profile from recent data.

    Call this after studying for a while to update the system's
    understanding of how you learn best.
    """
    profile = analyze_learning_style()
    return (
        f"✅ Profile updated based on {profile['data_points']} data points.\n"
        f"Teaching style: {profile['teaching_style']}\n"
        f"Preferred time: {profile['preferred_time']}\n"
        f"Optimal session: {profile['preferred_session_length_min']} min"
    )


# ── Career & Academic Growth ────────────────────────────────────

@tool
def manage_skill(action: str, name: str = "", xp: int = 0,
                 topic: str = "", category: str = "general") -> str:
    """Track your skills with XP and levels.

    Actions:
    - 'add': Register a new skill (provide 'name' and optional 'category')
    - 'add_xp': Add XP to a skill (provide 'name' and 'xp')
    - 'list': Show all tracked skills
    """
    action = action.lower().strip()
    if action == "add":
        return add_skill(name, category)
    elif action == "add_xp":
        return update_skill_xp(name, xp, topic)
    elif action == "list":
        return get_skills()
    return f"Unknown action. Use: add, add_xp, or list."


@tool
def manage_milestone(action: str, title: str = "",
                     milestone_type: str = "general", notes: str = "") -> str:
    """Record and view career/academic milestones.

    Actions:
    - 'add': Record a milestone (provide 'title' and optional 'type' and 'notes')
    - 'list': Show all milestones
    """
    action = action.lower().strip()
    if action == "add":
        return add_milestone(title, milestone_type, notes)
    elif action == "list":
        return get_milestones()
    return f"Unknown action. Use: add or list."


@tool
def manage_academic_goal(action: str, subject: str = "",
                         target: str = "", deadline: str = "") -> str:
    """Set and track academic goals.

    Actions:
    - 'set': Create a goal (provide 'subject', 'target', optional 'deadline')
    - 'list': Show active goals
    """
    action = action.lower().strip()
    if action == "set":
        return set_academic_goal(subject, target, deadline)
    elif action == "list":
        return get_academic_goals()
    return f"Unknown action. Use: set or list."


@tool
def manage_career_goal(action: str, goal: str = "",
                       skills_needed: str = "", deadline: str = "") -> str:
    """Set and track career goals.

    Actions:
    - 'set': Create a goal (provide 'goal', optional 'skills_needed', 'deadline')
    - 'list': Show active goals
    """
    action = action.lower().strip()
    if action == "set":
        return set_career_goal(goal, skills_needed, deadline)
    elif action == "list":
        return get_career_goals()
    return f"Unknown action. Use: set or list."


@tool
def get_growth_report() -> str:
    """Get your comprehensive growth report — levels, XP, skills, milestones, goals."""
    from ..always_on.growth import get_growth_report as _report
    return _report()


@tool
def earn_xp(amount: int, reason: str = "") -> str:
    """Award XP to the user for completing something (manual XP boost).

    Parameters:
    - amount: XP to award (1-100)
    - reason: Why they're earning XP
    """
    amount = max(1, min(100, amount))
    result = add_xp(amount, reason)
    msg = f"✨ +{amount} XP! Total: {result['total_xp']} (Level {result['level']})"
    if reason:
        msg += f"\nReason: {reason}"
    if result["leveled_up"]:
        msg += f"\n🎉 LEVEL UP! You're now Level {result['level']}!"
    return msg
