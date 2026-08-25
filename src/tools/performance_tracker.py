"""
Performance Tracker tool — records study activity into the analytics DB
so the bandit can learn and the dashboard can visualize.
"""

from langchain_core.tools import tool

from ..analytics.bandit import (
    compute_reward_from_confidence,
    compute_reward_from_flashcard,
    compute_reward_from_quiz,
    update_reward,
)
from ..analytics.queries import (
    get_method_effectiveness,
    get_overview_stats,
    get_streak,
    get_topic_breakdown,
    get_weak_topics,
    record_flashcard_review,
    record_quiz,
    record_session,
)


@tool
def track_study_session(
    topic: str,
    method: str,
    duration_min: float = 30,
    score_before: float = 0,
    score_after: float = 0,
    confidence: float = 3,
    notes: str = "",
) -> str:
    """Record a study session to track your progress and learning.

    Call this AFTER studying a topic to log what you did. The system uses this
    data to learn which methods work best for you.

    Parameters:
    - topic: What you studied (e.g., "binary trees", "OSI model", "Python decorators")
    - method: Study method used. Pick from:
        flashcards, active_recall, pomodoro, interleaving, elaboration,
        practice_problems, mind_mapping, teach_back, cornell_notes,
        retrieval_practice
    - duration_min: How long you studied in minutes
    - score_before: Confidence/knowledge score before (1-5 scale, 0 if unknown)
    - score_after: Confidence/knowledge score after (1-5 scale, 0 if unknown)
    - confidence: How confident you feel now (1-5, where 5 = very confident)
    - notes: Optional notes about the session
    """
    topic = topic.strip()
    method = method.strip().lower().replace(" ", "_").replace("-", "_")

    session_id = record_session(
        topic=topic,
        method=method,
        duration_min=max(0, duration_min),
        score_before=score_before if score_before > 0 else None,
        score_after=score_after if score_after > 0 else None,
        confidence=confidence,
        notes=notes,
    )

    # Feed reward to bandit based on post-study confidence
    reward = compute_reward_from_confidence(confidence)
    update_reward(method, reward, topic)

    improvement = ""
    if score_before > 0 and score_after > 0:
        delta = score_after - score_before
        if delta > 0:
            improvement = f" (+{delta:.1f} improvement)"
        elif delta < 0:
            improvement = f" ({delta:.1f} regression)"
        else:
            improvement = " (no change)"

    return (
        f"📊 Logged study session #{session_id}:\n"
        f"   Topic: {topic}\n"
        f"   Method: {method}\n"
        f"   Duration: {duration_min:.0f} min\n"
        f"   Confidence: {confidence}/5{improvement}\n"
        f"   Reward sent to bandit: {reward:.2f}"
    )


@tool
def record_quiz_result(
    topic: str,
    score: float,
    total: int,
    difficulty: str = "medium",
    method: str = "general",
    time_spent: float = 0,
) -> str:
    """Record a quiz/test result to track your understanding.

    Call this after taking a quiz or test. This feeds into your analytics
    and helps the system learn which study methods improve your scores.

    Parameters:
    - topic: What the quiz was about
    - score: Number of correct answers
    - total: Total number of questions
    - difficulty: 'easy', 'medium', or 'hard'
    - method: Study method you used to prepare (same as track_study_session methods)
    - time_spent: Time spent on the quiz in minutes (0 if unknown)
    """
    topic = topic.strip()
    method = method.strip().lower().replace(" ", "_").replace("-", "_")

    quiz_id = record_quiz(
        topic=topic, score=score, total=total,
        difficulty=difficulty, method=method, time_spent=time_spent,
    )

    # Feed reward to bandit based on quiz performance
    reward = compute_reward_from_quiz(score, total)
    if method != "general":
        update_reward(method, reward, topic)

    pct = (score / total * 100) if total > 0 else 0
    emoji = "🟢" if pct >= 80 else "🟡" if pct >= 60 else "🔴"

    return (
        f"{emoji} Recorded quiz #{quiz_id}:\n"
        f"   Topic: {topic} ({difficulty})\n"
        f"   Score: {score}/{total} ({pct:.0f}%)\n"
        f"   Method used: {method}\n"
        f"   Bandit reward: {reward:.2f}"
    )


@tool
def record_flashcard_review_result(
    card_id: int,
    topic: str,
    rating: str,
    ease_factor: float = 2.5,
    interval_days: float = 1,
    time_taken: float = 0,
) -> str:
    """Record a flashcard review result into analytics (call after rating a card).

    This supplements the flashcard tool's own tracking with richer analytics.
    """
    topic = topic.strip()
    rating = rating.strip().lower()

    review_id = record_flashcard_review(
        card_id=card_id, topic=topic, rating=rating,
        ease_factor=ease_factor, interval_days=interval_days,
        time_taken=time_taken,
    )

    reward = compute_reward_from_flashcard(rating)
    update_reward("flashcards", reward, topic)

    return (
        f"📝 Logged flashcard review #{review_id}: "
        f"card={card_id}, rating={rating}, reward={reward:.2f}"
    )


@tool
def get_performance_report(period: str = "30d") -> str:
    """Get your learning performance report with stats and insights.

    Parameters:
    - period: '7d', '30d', or '90d' for the reporting window
    """
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(period, 30)

    overview = get_overview_stats(days)
    streak = get_streak()
    weak = get_weak_topics(5)
    topics = get_topic_breakdown(days)
    methods = get_method_effectiveness(days)

    lines = [
        f"📊 **Performance Report (last {days} days)**\n",
        f"🔥 Study streak: {streak['current_streak']} days (best: {streak['longest_streak']})",
        f"📚 Study sessions: {overview['total_sessions']}",
        f"⏱️  Total study time: {overview['total_study_minutes']} min",
        f"📝 Quizzes taken: {overview['total_quizzes']}",
        f"📈 Average quiz score: {overview['avg_quiz_score']}%",
        f"🃏 Flashcard reviews: {overview['total_flashcard_reviews']}",
    ]

    if overview["topics_studied"]:
        lines.append(f"\n📂 Topics studied: {', '.join(overview['topics_studied'])}")

    if topics:
        lines.append("\n**Time by topic:**")
        for t in topics[:5]:
            lines.append(f"  • {t['topic']}: {t['minutes']:.0f} min ({t['sessions']} sessions)")

    if methods:
        lines.append("\n**Method effectiveness:**")
        for m in methods[:5]:
            bar = "█" * int(m["avg_reward"] * 10) + "░" * (10 - int(m["avg_reward"] * 10))
            lines.append(f"  • {m['method']}: {bar} {m['avg_reward']:.0%} (n={m['uses']})")

    if weak:
        lines.append("\n⚠️ **Weak topics (need review):**")
        for w in weak:
            lines.append(f"  • {w['topic']}: {w['avg_score']}% avg ({w['attempts']} quizzes)")

    if not overview["total_sessions"] and not overview["total_quizzes"]:
        lines.append("\n💡 No data yet! Start tracking by logging study sessions "
                     "and quiz results. The more data, the smarter my recommendations.")

    return "\n".join(lines)
