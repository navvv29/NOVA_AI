import json
import os
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

TODO_FILE = os.getenv("NOVA_TODO_FILE", "nova_todos.json")


def _load_todos() -> list[dict]:
    """Load todos from the JSON file."""
    path = Path(TODO_FILE)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_todos(todos: list[dict]) -> None:
    """Save todos to the JSON file."""
    path = Path(TODO_FILE)
    path.write_text(json.dumps(todos, indent=2, ensure_ascii=False), encoding="utf-8")


@tool
def manage_todo(
    action: str,
    task: str = "",
    todo_id: int = 0,
    priority: str = "medium",
    due_date: str = "",
    category: str = "general",
) -> str:
    """Manage your tasks, assignments, and study goals.

    Actions:
    - 'add': Add a new task. Provide 'task' description, optional 'priority' (high/medium/low),
      optional 'due_date' (YYYY-MM-DD), and optional 'category' (study/assignment/project/general).
    - 'list': List all tasks. Optionally filter by 'category'.
    - 'complete': Mark a task as done. Provide 'todo_id' (the task number).
    - 'delete': Delete a task. Provide 'todo_id'.
    - 'stats': Show summary statistics of your tasks.
    """
    todos = _load_todos()
    action = action.lower().strip()

    if action == "add":
        if not task.strip():
            return "Error: Please provide a task description."
        new_id = max((t["id"] for t in todos), default=0) + 1
        new_todo = {
            "id": new_id,
            "task": task.strip(),
            "priority": priority.lower() if priority.lower() in ("high", "medium", "low") else "medium",
            "due_date": due_date.strip() if due_date.strip() else None,
            "category": category.lower() if category.lower() in ("study", "assignment", "project", "general") else "general",
            "completed": False,
            "created_at": datetime.now().isoformat(),
        }
        todos.append(new_todo)
        _save_todos(todos)
        return f"✅ Added task #{new_id}: {task.strip()} [{new_todo['priority']}] [{new_todo['category']}]"

    elif action == "list":
        if not todos:
            return "No tasks yet. Use 'add' to create one!"
        
        # Filter by category if provided
        if category and category.lower() != "general":
            filtered = [t for t in todos if t.get("category") == category.lower()]
        else:
            filtered = todos

        if not filtered:
            return f"No tasks found in category '{category}'."

        # Sort: incomplete first, then by priority, then by due date
        priority_order = {"high": 0, "medium": 1, "low": 2}
        filtered.sort(key=lambda t: (
            t["completed"],
            priority_order.get(t.get("priority", "medium"), 1),
            t.get("due_date") or "9999-99-99",
        ))

        lines = ["📋 **Your Tasks:**\n"]
        for t in filtered:
            status = "✅" if t["completed"] else "⬜"
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.get("priority", "medium"), "⚪")
            due = f" (due: {t['due_date']})" if t.get("due_date") else ""
            category_tag = f" [{t.get('category', 'general')}]"
            lines.append(f"{status} #{t['id']} {priority_icon} {t['task']}{due}{category_tag}")
        
        completed = sum(1 for t in todos if t["completed"])
        lines.append(f"\n📊 {completed}/{len(todos)} tasks completed")
        return "\n".join(lines)

    elif action == "complete":
        for t in todos:
            if t["id"] == todo_id:
                t["completed"] = True
                t["completed_at"] = datetime.now().isoformat()
                _save_todos(todos)
                return f"🎉 Completed task #{todo_id}: {t['task']}"
        return f"Task #{todo_id} not found."

    elif action == "delete":
        original_len = len(todos)
        todos = [t for t in todos if t["id"] != todo_id]
        if len(todos) < original_len:
            _save_todos(todos)
            return f"🗑️ Deleted task #{todo_id}."
        return f"Task #{todo_id} not found."

    elif action == "stats":
        if not todos:
            return "No tasks yet."
        
        total = len(todos)
        completed = sum(1 for t in todos if t["completed"])
        pending = total - completed
        
        high = sum(1 for t in todos if not t["completed"] and t.get("priority") == "high")
        overdue = sum(
            1 for t in todos
            if not t["completed"]
            and t.get("due_date")
            and t["due_date"] < datetime.now().strftime("%Y-%m-%d")
        )
        
        categories = {}
        for t in todos:
            cat = t.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
        
        stats = [
            f"📊 **Task Statistics:**",
            f"• Total: {total}",
            f"• Completed: {completed} ({completed/total*100:.0f}%)",
            f"• Pending: {pending}",
            f"• High priority: {high}",
            f"• Overdue: {overdue}",
            f"\n📂 By category:",
        ]
        for cat, count in sorted(categories.items()):
            stats.append(f"  • {cat}: {count}")
        
        return "\n".join(stats)

    else:
        return f"Unknown action '{action}'. Use: add, list, complete, delete, or stats."
