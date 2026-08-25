"""
Adaptive Study Recommender — uses the multi-armed bandit + performance
analytics to suggest personalized study strategies.
"""

from datetime import datetime

from langchain_core.tools import tool

from ..analytics.bandit import (
    ALL_METHODS,
    arm_summary,
    get_rankings,
    thompson_select,
)
from ..analytics.queries import get_streak, get_topic_breakdown, get_weak_topics


@tool
def get_study_recommendation(
    topic: str = "",
    current_method: str = "",
) -> str:
    """Get a personalized study recommendation based on your performance data.

    Uses Thompson Sampling (multi-armed bandit) to balance what's worked
    before with exploring new methods. The more you track, the better
    the recommendations get.

    Parameters:
    - topic: What you plan to study (for topic-specific recommendations)
    - current_method: What you're currently using (to suggest alternatives)
    """
    topic = topic.strip() if topic else None
    current_method = current_method.strip().lower().replace(" ", "_") if current_method else None

    # Get bandit's top recommendations
    top_methods = thompson_select(topic=topic, n=3, days=60)

    # Get weak topics that need attention
    weak = get_weak_topics(3)

    # Get topic distribution
    topics = get_topic_breakdown(30)
    streak = get_streak()

    lines = ["🎯 **Adaptive Study Recommendation:**\n"]

    # Primary recommendation from bandit
    best = top_methods[0]
    lines.append(f"**Best method for you right now:** {best['method'].replace('_', ' ').title()}")
    lines.append(f"  (estimated success rate: {best['mean']:.0%} based on {best['pulls']} past uses)\n")

    # If there's a weak topic, tie it in
    if weak:
        weakest = weak[0]
        lines.append(f"**Priority topic:** {weakest['topic']} "
                     f"(only {weakest['avg_score']}% avg — needs review)\n")

    # Top 3 methods ranked
    lines.append("**Your top 3 methods (by Thompson Sampling):**")
    for i, m in enumerate(top_methods, 1):
        label = m["method"].replace("_", " ").title()
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        lines.append(f"  {emoji} {label}: {m['mean']:.0%} (sampled: {m['sampled_value']:.3f})")

    # Suggest alternative if they're using something suboptimal
    if current_method:
        current_rank = next((i for i, m in enumerate(top_methods) if m["method"] == current_method), None)
        if current_rank is None or current_rank > 0:
            alt = next((m for m in top_methods if m["method"] != current_method), None)
            if alt:
                lines.append(f"\n💡 You're using **{current_method.replace('_', ' ')}** — "
                             f"try **{alt['method'].replace('_', ' ')}** as a complement.")

    # Learning streak encouragement
    if streak["current_streak"] > 0:
        lines.append(f"\n🔥 {streak['current_streak']}-day streak! Keep it up!")
    else:
        lines.append(f"\n💪 Start a study session today to build a streak!")

    # Balance recommendation: which topics need more time
    if topics:
        min_topic = min(topics, key=lambda t: t["minutes"])
        lines.append(f"\n📊 Consider spending more time on **{min_topic['topic']}** "
                     f"({min_topic['minutes']:.0f} min total)")

    return "\n".join(lines)


@tool
def get_method_rankings(topic: str = "") -> str:
    """Show how all study methods rank for you, with detailed stats.

    Parameters:
    - topic: Optional topic filter to see method rankings for a specific subject
    """
    topic = topic.strip() if topic else None

    rankings = get_rankings(topic=topic, days=60)
    topic_label = f" (filtered to: {topic})" if topic else ""

    lines = [f"📈 **Method Rankings{topic_label}:**\n"]

    for i, r in enumerate(rankings, 1):
        label = r["method"].replace("_", " ").title()
        mean = r["mean"]
        n = r["pulls"]

        # Confidence indicator
        if n >= 10:
            conf = "✅ confident"
        elif n >= 5:
            conf = "📊 building"
        else:
            conf = "🔬 exploring"

        bar_len = int(mean * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)

        lines.append(
            f"  {i}. {label}\n"
            f"     {bar} {mean:.0%}  ({n} uses) [{conf}]"
        )

    return "\n".join(lines)


@tool
def get_bandit_insights() -> str:
    """Get raw multi-armed bandit diagnostic data — see the math behind recommendations.

    Shows posterior distributions, variance (uncertainty), and exploration status
    for each study method arm.
    """
    topic = None
    from ..analytics.bandit import _load_posteriors
    stats = _load_posteriors(topic, days=90)

    lines = ["🔬 **Bandit Diagnostics (Thompson Sampling):**\n"]
    lines.append("Method | α | β | Mean | Variance | Pulls | Status")
    lines.append("-------|---|---|------|----------|-------|-------")

    for arm in sorted(stats.values(), key=lambda a: a.mean, reverse=True):
        if arm.pulls == 0:
            status = "untouched"
        elif arm.pulls < 3:
            status = "exploring"
        elif arm.variance > 0.02:
            status = "uncertain"
        else:
            status = "exploiting"

        lines.append(
            f"{arm.method:20s} | {arm.alpha:.1f} | {arm.beta:.1f} | "
            f"{arm.mean:.3f} | {arm.variance:.5f} | {arm.pulls:5d} | {status}"
        )

    lines.append("\n**How it works:**")
    lines.append("• Thompson Sampling draws from each method's Beta distribution")
    lines.append("• Higher α = more observed rewards (successes)")
    lines.append("• Higher β = more observed failures")
    lines.append("• Variance = uncertainty — high variance means 'try this more'")
    lines.append("• 'exploring' arms need more data before we trust their ranking")

    return "\n".join(lines)
