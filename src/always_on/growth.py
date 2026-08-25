"""
Career & Academic Growth Tracker.

Tracks:
  - Skills learned and proficiency levels
  - Career milestones (projects, certifications, internships)
  - Academic goals (GPA targets, course completion)
  - Skill tree dependencies (learn X before Y)
  - Growth over time
"""

import json
from datetime import datetime
from pathlib import Path

GROWTH_FILE = Path("nova_growth.json")


def _load_growth() -> dict:
    if GROWTH_FILE.exists():
        try:
            return json.loads(GROWTH_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "skills": {},  # {name: {"level": 1, "xp": 0, "topics": [], "updated": ...}}
        "milestones": [],  # [{title, type, date, notes, completed}]
        "academic_goals": [],  # [{subject, target, current, deadline, status}]
        "career_goals": [],  # [{goal, skills_needed, progress, deadline}]
        "weekly_xp": {},  # {"2026-W34": 120}
        "total_xp": 0,
        "level": 1,
    }


def _save_growth(data: dict):
    GROWTH_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# XP system
XP_PER_SESSION = 10
XP_PER_QUIZ_PASS = 20
XP_PER_QUIZ_PERFECT = 50
XP_PER_STREAK_DAY = 5
LEVEL_THRESHOLDS = [0, 50, 150, 300, 500, 800, 1200, 1800, 2500, 3500, 5000]


def _calc_level(xp: int) -> int:
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp < threshold:
            return max(1, i)
    return len(LEVEL_THRESHOLDS) + (xp - LEVEL_THRESHOLDS[-1]) // 1000


def add_xp(amount: int, source: str = "") -> dict:
    """Add XP and check for level up."""
    growth = _load_growth()
    old_level = growth["level"]
    growth["total_xp"] += amount
    growth["level"] = _calc_level(growth["total_xp"])

    # Track weekly XP
    week = datetime.now().strftime("%G-W%V")
    growth["weekly_xp"][week] = growth["weekly_xp"].get(week, 0) + amount

    _save_growth(growth)

    leveled_up = growth["level"] > old_level
    return {
        "xp_gained": amount,
        "total_xp": growth["total_xp"],
        "level": growth["level"],
        "leveled_up": leveled_up,
        "source": source,
    }


# ── Skills ──────────────────────────────────────────────────────

def add_skill(name: str, category: str = "general") -> str:
    """Register a skill being learned."""
    growth = _load_growth()
    name = name.strip().lower()
    if name not in growth["skills"]:
        growth["skills"][name] = {
            "level": 1, "xp": 0, "category": category,
            "topics": [], "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }
        _save_growth(growth)
        return f"🎯 New skill registered: {name.title()} (Level 1)"
    return f"Skill '{name.title()}' already tracked."


def update_skill_xp(name: str, xp: int, topic: str = "") -> str:
    """Add XP to a specific skill."""
    growth = _load_growth()
    name = name.strip().lower()
    if name not in growth["skills"]:
        add_skill(name)
        growth = _load_growth()

    skill = growth["skills"][name]
    skill["xp"] += xp
    skill["updated"] = datetime.now().isoformat()
    if topic and topic not in skill["topics"]:
        skill["topics"].append(topic)

    # Level up thresholds: 50, 120, 220, 360, ...
    thresholds = [50, 120, 220, 360, 550, 800, 1100, 1500, 2000]
    new_level = 1
    for i, t in enumerate(thresholds):
        if skill["xp"] >= t:
            new_level = i + 2

    leveled_up = new_level > skill["level"]
    skill["level"] = new_level
    _save_growth(growth)

    if leveled_up:
        return f"🎉 {name.title()} leveled up to Level {new_level}!"
    return f"+{xp} XP to {name.title()} (Level {skill['level']}, {skill['xp']} total XP)"


def get_skills() -> str:
    """Show all tracked skills."""
    growth = _load_growth()
    if not growth["skills"]:
        return "No skills tracked yet. Start studying and I'll track them automatically!"

    lines = [f"🎯 **Skills** (Level {growth['level']}, {growth['total_xp']} XP)\n"]
    sorted_skills = sorted(growth["skills"].items(), key=lambda x: x[1]["xp"], reverse=True)

    for name, skill in sorted_skills:
        level = skill["level"]
        xp = skill["xp"]
        cat = skill.get("category", "general")
        bar_len = min(10, xp // 30)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        lines.append(f"  Lv.{level} {name.title():20s} {bar} {xp} XP [{cat}]")

    return "\n".join(lines)


# ── Milestones ──────────────────────────────────────────────────

def add_milestone(title: str, milestone_type: str = "general", notes: str = "") -> str:
    """Record a career/academic milestone."""
    growth = _load_growth()
    ms = {
        "title": title,
        "type": milestone_type,  # project, certification, course, internship, achievement
        "date": datetime.now().isoformat(),
        "notes": notes,
        "completed": True,
    }
    growth["milestones"].append(ms)
    _save_growth(growth)
    return f"🏆 Milestone recorded: {title} ({milestone_type})"


def get_milestones() -> str:
    """Show all milestones."""
    growth = _load_growth()
    if not growth["milestones"]:
        return "No milestones yet. Record your achievements as you go!"

    lines = ["🏆 **Milestones:**\n"]
    for ms in reversed(growth["milestones"]):
        date = ms["date"][:10]
        lines.append(f"  • [{ms['type']}] {ms['title']} — {date}")
        if ms.get("notes"):
            lines.append(f"    {ms['notes']}")
    return "\n".join(lines)


# ── Academic Goals ──────────────────────────────────────────────

def set_academic_goal(subject: str, target: str, deadline: str = "") -> str:
    """Set an academic goal (e.g., GPA 8.0 by end of semester)."""
    growth = _load_growth()
    goal = {
        "subject": subject,
        "target": target,
        "current": "not started",
        "deadline": deadline,
        "status": "active",
        "created": datetime.now().isoformat(),
    }
    growth["academic_goals"].append(goal)
    _save_growth(growth)
    return f"📚 Academic goal set: {subject} → {target}" + (f" by {deadline}" if deadline else "")


def get_academic_goals() -> str:
    growth = _load_growth()
    active = [g for g in growth["academic_goals"] if g["status"] == "active"]
    if not active:
        return "No active academic goals. Use 'set_academic_goal' to add one!"

    lines = ["📚 **Academic Goals:**\n"]
    for g in active:
        deadline = f" (due: {g['deadline']})" if g.get("deadline") else ""
        lines.append(f"  • {g['subject']}: {g['target']}{deadline}")
    return "\n".join(lines)


# ── Career Goals ────────────────────────────────────────────────

def set_career_goal(goal: str, skills_needed: str = "", deadline: str = "") -> str:
    growth = _load_growth()
    entry = {
        "goal": goal,
        "skills_needed": [s.strip() for s in skills_needed.split(",") if s.strip()] if skills_needed else [],
        "progress": 0,
        "deadline": deadline,
        "status": "active",
        "created": datetime.now().isoformat(),
    }
    growth["career_goals"].append(entry)
    _save_growth(growth)
    return f"🚀 Career goal set: {goal}"


def get_career_goals() -> str:
    growth = _load_growth()
    active = [g for g in growth["career_goals"] if g["status"] == "active"]
    if not active:
        return "No career goals yet. Think about where you want to be in 1-2 years!"

    lines = ["🚀 **Career Goals:**\n"]
    for g in active:
        skills = ", ".join(g.get("skills_needed", []))
        deadline = f" (by {g['deadline']})" if g.get("deadline") else ""
        lines.append(f"  • {g['goal']}{deadline}")
        if skills:
            lines.append(f"    Skills needed: {skills}")
    return "\n".join(lines)


# ── Growth Report ───────────────────────────────────────────────

def get_growth_report() -> str:
    """Comprehensive growth report."""
    growth = _load_growth()

    lines = [
        f"📈 **Growth Report**\n",
        f"**Level:** {growth['level']} | **Total XP:** {growth['total_xp']}",
        f"**Skills tracked:** {len(growth['skills'])}",
        f"**Milestones:** {len(growth['milestones'])}",
        f"**Academic goals:** {len([g for g in growth['academic_goals'] if g['status'] == 'active'])}",
        f"**Career goals:** {len([g for g in growth['career_goals'] if g['status'] == 'active'])}",
    ]

    # Weekly XP trend
    weeks = sorted(growth["weekly_xp"].items(), reverse=True)[:4]
    if weeks:
        lines.append("\n**Weekly XP:**")
        for week, xp in weeks:
            bar = "█" * min(20, xp // 5) + "░" * max(0, 20 - xp // 5)
            lines.append(f"  {week}: {bar} {xp} XP")

    # Top skills
    if growth["skills"]:
        top = sorted(growth["skills"].items(), key=lambda x: x[1]["xp"], reverse=True)[:5]
        lines.append("\n**Top Skills:**")
        for name, s in top:
            lines.append(f"  • {name.title()}: Level {s['level']} ({s['xp']} XP)")

    return "\n".join(lines)
