import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

from langchain_core.tools import tool

FLASHCARD_FILE = os.getenv("NOVA_FLASHCARD_FILE", "nova_flashcards.json")


def _load_flashcards() -> list[dict]:
    path = Path(FLASHCARD_FILE)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_flashcards(cards: list[dict]) -> None:
    path = Path(FLASHCARD_FILE)
    path.write_text(json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8")


@tool
def manage_flashcards(
    action: str,
    topic: str = "",
    front: str = "",
    back: str = "",
    card_id: int = 0,
    category: str = "general",
) -> str:
    """Manage flashcards for studying with spaced repetition.

    Actions:
    - 'create': Create a flashcard. Provide 'front' (question/term) and 'back' (answer/definition),
      optional 'topic' and 'category'.
    - 'create_batch': Create multiple flashcards at once. Provide 'front' with cards separated by '|||' and
      'back' with corresponding answers separated by '|||'. Optional 'topic'.
    - 'review': Get cards due for review (spaced repetition).
    - 'quiz_me': Get a random card and ask the user to recall the answer (shows only the front).
    - 'show_answer': Reveal the answer for a specific card (provide 'card_id').
    - 'rate': Rate how well you knew a card. Provide 'card_id' and 'front' as rating:
      'again' (didn't know), 'hard' (struggled), 'good' (remembered), 'easy' (instant recall).
    - 'list': List all cards for a topic or category.
    - 'stats': Show study statistics.
    - 'delete': Delete a card (provide 'card_id').
    """
    cards = _load_flashcards()
    action = action.lower().strip()

    if action == "create":
        if not front.strip() or not back.strip():
            return "Error: Provide both 'front' and 'back' for the flashcard."
        new_id = max((c["id"] for c in cards), default=0) + 1
        new_card = {
            "id": new_id,
            "front": front.strip(),
            "back": back.strip(),
            "topic": topic.strip() if topic.strip() else "general",
            "category": category.strip() if category.strip() else "general",
            "created_at": datetime.now().isoformat(),
            "next_review": datetime.now().isoformat(),
            "interval_days": 1,
            "ease_factor": 2.5,
            "reviews": 0,
        }
        cards.append(new_card)
        _save_flashcards(cards)
        return f"🃏 Created flashcard #{new_id}:\n   Q: {front.strip()}\n   A: {back.strip()}"

    elif action == "create_batch":
        fronts = [f.strip() for f in front.split("|||") if f.strip()]
        backs = [b.strip() for b in back.split("|||") if b.strip()]
        if len(fronts) != len(backs):
            return f"Error: Mismatch — {len(fronts)} fronts but {len(backs)} backs. Must be equal."
        if not fronts:
            return "Error: No flashcards provided."
        
        created = []
        base_id = max((c["id"] for c in cards), default=0)
        for i, (f, b) in enumerate(zip(fronts, backs)):
            new_id = base_id + i + 1
            cards.append({
                "id": new_id,
                "front": f,
                "back": b,
                "topic": topic.strip() if topic.strip() else "general",
                "category": category.strip() if category.strip() else "general",
                "created_at": datetime.now().isoformat(),
                "next_review": datetime.now().isoformat(),
                "interval_days": 1,
                "ease_factor": 2.5,
                "reviews": 0,
            })
            created.append(f"#{new_id}: {f}")
        
        _save_flashcards(cards)
        return f"🃏 Created {len(created)} flashcards:\n" + "\n".join(created)

    elif action == "review":
        now = datetime.now()
        due = [c for c in cards if datetime.fromisoformat(c["next_review"]) <= now]
        if not due:
            return "🎉 No cards due for review right now! Great job keeping up."
        
        # Sort by overdue-ness (most overdue first)
        due.sort(key=lambda c: c["next_review"])
        
        lines = [f"📚 **{len(due)} card(s) due for review:**\n"]
        for c in due[:10]:  # Show max 10
            lines.append(f"#{c['id']} [{c['topic']}] Q: {c['front']}")
        if len(due) > 10:
            lines.append(f"\n... and {len(due) - 10} more.")
        lines.append("\nUse 'quiz_me' to start reviewing!")
        return "\n".join(lines)

    elif action == "quiz_me":
        if not cards:
            return "No flashcards yet! Use 'create' or 'create_batch' to add some."
        
        # Prefer cards due for review, then random
        now = datetime.now()
        due = [c for c in cards if datetime.fromisoformat(c["next_review"]) <= now]
        pool = due if due else cards
        card = random.choice(pool)
        
        return (
            f"🧠 **Quiz Time!** (Card #{card['id']})\n"
            f"**Topic:** {card.get('topic', 'general')}\n\n"
            f"**Q:** {card['front']}\n\n"
            f"Think of your answer, then use 'show_answer' with card_id={card['id']} to check."
        )

    elif action == "show_answer":
        for c in cards:
            if c["id"] == card_id:
                return (
                    f"🃏 **Card #{card_id}:**\n"
                    f"**Q:** {c['front']}\n\n"
                    f"**A:** {c['back']}\n\n"
                    f"How well did you know it? Use 'rate' with card_id={card_id} and:\n"
                    f"- 'again' (didn't know at all)\n"
                    f"- 'hard' (struggled but got it)\n"
                    f"- 'good' (remembered correctly)\n"
                    f"- 'easy' (instant, perfect recall)"
                )
        return f"Card #{card_id} not found."

    elif action == "rate":
        for c in cards:
            if c["id"] == card_id:
                rating = front.strip().lower()  # reuse front param as rating
                if rating not in ("again", "hard", "good", "easy"):
                    return "Rating must be: again, hard, good, or easy."
                
                # SM-2 algorithm (simplified)
                c["reviews"] = c.get("reviews", 0) + 1
                
                if rating == "again":
                    c["interval_days"] = 1
                    c["ease_factor"] = max(1.3, c["ease_factor"] - 0.2)
                elif rating == "hard":
                    c["interval_days"] = max(1, int(c["interval_days"] * 1.2))
                    c["ease_factor"] = max(1.3, c["ease_factor"] - 0.15)
                elif rating == "good":
                    c["interval_days"] = max(1, int(c["interval_days"] * c["ease_factor"]))
                elif rating == "easy":
                    c["interval_days"] = max(1, int(c["interval_days"] * c["ease_factor"] * 1.3))
                    c["ease_factor"] = min(3.0, c["ease_factor"] + 0.15)
                
                next_review = datetime.now() + timedelta(days=c["interval_days"])
                c["next_review"] = next_review.isoformat()
                
                _save_flashcards(cards)
                return (
                    f"📝 Rated card #{card_id} as '{rating}'\n"
                    f"Next review in {c['interval_days']} day(s) "
                    f"(on {next_review.strftime('%Y-%m-%d')})"
                )
        return f"Card #{card_id} not found."

    elif action == "list":
        filtered = cards
        if topic.strip():
            filtered = [c for c in cards if c.get("topic", "").lower() == topic.lower()]
        if category.strip() and category.lower() != "general":
            filtered = [c for c in filtered if c.get("category", "").lower() == category.lower()]
        
        if not filtered:
            return "No flashcards found."
        
        lines = [f"🃏 **{len(filtered)} flashcard(s):**\n"]
        for c in filtered:
            lines.append(f"#{c['id']} [{c.get('topic', 'general')}] Q: {c['front'][:60]}...")
        return "\n".join(lines)

    elif action == "stats":
        if not cards:
            return "No flashcards yet."
        
        total = len(cards)
        now = datetime.now()
        due = sum(1 for c in cards if datetime.fromisoformat(c["next_review"]) <= now)
        reviewed = sum(1 for c in cards if c.get("reviews", 0) > 0)
        avg_ease = sum(c.get("ease_factor", 2.5) for c in cards) / total
        
        categories = {}
        for c in cards:
            cat = c.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
        
        stats = [
            f"🃏 **Flashcard Statistics:**",
            f"• Total cards: {total}",
            f"• Due for review: {due}",
            f"• Cards reviewed at least once: {reviewed}",
            f"• Average ease factor: {avg_ease:.2f}",
            f"\n📂 By category:",
        ]
        for cat, count in sorted(categories.items()):
            stats.append(f"  • {cat}: {count}")
        return "\n".join(stats)

    elif action == "delete":
        original_len = len(cards)
        cards = [c for c in cards if c["id"] != card_id]
        if len(cards) < original_len:
            _save_flashcards(cards)
            return f"🗑️ Deleted flashcard #{card_id}."
        return f"Card #{card_id} not found."

    else:
        return f"Unknown action '{action}'. Use: create, create_batch, review, quiz_me, show_answer, rate, list, stats, or delete."
