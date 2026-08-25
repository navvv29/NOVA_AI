"""
Multi-Armed Bandit — Thompson Sampling for study method selection.

Study methods are "arms". Each arm has a Beta(alpha, beta) posterior
updated by observed rewards (success/failure from quiz scores, flashcard
ratings, self-reported confidence, etc.).

Thompson Sampling naturally balances exploration (trying less-tested
methods) and exploitation (picking methods that have worked well).

Arms / methods:
  - flashcards          — spaced repetition review
  - active_recall       — self-testing without looking at notes
  - pomodoro            — timed focused sessions
  - interleaving        — mixing topics in one study session
  - elaboration         — explaining concepts in own words
  - practice_problems   — solving exercises / past papers
  - mind_mapping        — visual concept maps
  - teach_back           — teaching the concept to someone else
  -Cornell_notes        — structured note-taking
  - retrieval_practice  — closed-book recall after reading
"""

import math
import random
from dataclasses import dataclass, field

from .queries import get_method_rewards, record_method_reward

# Default arms — extensible
ALL_METHODS = [
    "flashcards",
    "active_recall",
    "pomodoro",
    "interleaving",
    "elaboration",
    "practice_problems",
    "mind_mapping",
    "teach_back",
    "cornell_notes",
    "retrieval_practice",
]

# Prior: uniform Beta(1, 1) for every arm
PRIOR_ALPHA = 1.0
PRIOR_BETA = 1.0


@dataclass
class ArmStats:
    method: str
    alpha: float = PRIOR_ALPHA
    beta: float = PRIOR_BETA
    pulls: int = 0

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    def sample(self) -> float:
        """Draw one sample from the Beta posterior (for Thompson Sampling)."""
        return random.betavariate(self.alpha, self.beta)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "alpha": round(self.alpha, 3),
            "beta": round(self.beta, 3),
            "mean": round(self.mean, 3),
            "variance": round(self.variance, 5),
            "pulls": self.pulls,
        }


def _load_posteriors(topic: str = None, days: int = 60) -> dict[str, ArmStats]:
    """Rebuild posterior distributions from reward history."""
    stats = {m: ArmStats(method=m) for m in ALL_METHODS}
    rewards = get_method_rewards(topic=topic, days=days)
    for r in rewards:
        m = r["method"]
        if m not in stats:
            stats[m] = ArmStats(method=m)
        reward = max(0.0, min(1.0, r["reward"]))  # clamp [0, 1]
        stats[m].alpha += reward
        stats[m].beta += (1 - reward)
        stats[m].pulls += 1
    return stats


def thompson_select(topic: str = None, n: int = 3,
                     days: int = 60) -> list[dict]:
    """
    Run one round of Thompson Sampling and return the top-n arms.

    Returns list of dicts sorted by sampled value (best first):
      [{"method": "active_recall", "sampled_value": 0.72, "mean": 0.65, ...}]
    """
    stats = _load_posteriors(topic, days)
    sampled = []
    for m, arm in stats.items():
        s = arm.sample()
        sampled.append({"method": m, "sampled_value": round(s, 4), **arm.to_dict()})
    sampled.sort(key=lambda x: x["sampled_value"], reverse=True)
    return sampled[:n]


def get_rankings(topic: str = None, days: int = 60) -> list[dict]:
    """Return all arms ranked by posterior mean (exploitation ranking)."""
    stats = _load_posteriors(topic, days)
    ranked = [arm.to_dict() for arm in stats.values()]
    ranked.sort(key=lambda x: x["mean"], reverse=True)
    return ranked


def update_reward(method: str, reward: float, topic: str = "general"):
    """
    Record a reward for a study method.

    reward should be 0.0–1.0 where:
      1.0 = full success (aced quiz, instant recall, high confidence)
      0.5 = partial success (struggled but got it)
      0.0 = failure (didn't know, gave up)
    """
    reward = max(0.0, min(1.0, reward))
    record_method_reward(method, reward, topic)


def compute_reward_from_quiz(score: float, total: int) -> float:
    """Convert a quiz score to a [0, 1] reward."""
    if total <= 0:
        return 0.5
    return max(0.0, min(1.0, score / total))


def compute_reward_from_flashcard(rating: str) -> float:
    """Convert a flashcard rating to a [0, 1] reward."""
    mapping = {"easy": 1.0, "good": 0.75, "hard": 0.4, "again": 0.1}
    return mapping.get(rating.lower(), 0.5)


def compute_reward_from_confidence(confidence: float) -> float:
    """Convert self-reported confidence (1-5 scale) to [0, 1]."""
    return max(0.0, min(1.0, (confidence - 1) / 4.0))


def arm_summary(topic: str = None, days: int = 60) -> str:
    """Human-readable summary of all arm posteriors."""
    stats = _load_posteriors(topic, days)
    lines = ["🎯 **Study Method Rankings (Thompson Sampling):**\n"]
    ranked = sorted(stats.values(), key=lambda a: a.mean, reverse=True)
    for i, arm in enumerate(ranked, 1):
        confidence = "🟢" if arm.pulls >= 5 else "🟡" if arm.pulls >= 2 else "⚪"
        lines.append(
            f"  {i}. {confidence} {arm.method}: "
            f"mean={arm.mean:.1%} (n={arm.pulls})"
        )
    lines.append("\n🟢 5+ uses | 🟡 2-4 uses | ⚪ <2 uses (more exploration needed)")
    return "\n".join(lines)
