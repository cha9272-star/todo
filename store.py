"""Shared data layer for the todo app (used by both the CLI and the web app).

Tasks are stored as JSON in todo.json next to this file. Each task has a
stable integer ``id`` so the web app can reference tasks safely regardless of
ordering or filtering.
"""

import json
from datetime import date, datetime
from pathlib import Path

DATA_FILE = Path(__file__).with_name("todo.json")

PRIORITIES = ("low", "medium", "high")
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
PRIORITY_LABEL = {"high": "!!!", "medium": "!!", "low": "!"}


class TaskError(Exception):
    """Raised for invalid input or missing tasks."""


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #

def load_tasks():
    """Load tasks, migrating older records to ensure every task has an id."""
    if not DATA_FILE.exists():
        return []
    try:
        tasks = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    changed = False
    next_id = max((t.get("id", 0) for t in tasks), default=0) + 1
    for task in tasks:
        if "id" not in task:
            task["id"] = next_id
            next_id += 1
            changed = True
    if changed:
        save_tasks(tasks)
    return tasks


def save_tasks(tasks):
    DATA_FILE.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #

def parse_due(value):
    """Validate/normalize a due date string (YYYY-MM-DD). Returns None or ISO date.

    Raises TaskError on an invalid date.
    """
    if value is None or value == "":
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise TaskError(f"invalid date '{value}', expected YYYY-MM-DD")


def normalize_priority(value):
    value = (value or "medium").lower()
    if value not in PRIORITIES:
        raise TaskError(f"invalid priority '{value}', expected one of {', '.join(PRIORITIES)}")
    return value


# --------------------------------------------------------------------------- #
# Mutations
# --------------------------------------------------------------------------- #

def add_task(text, due=None, priority="medium"):
    text = (text or "").strip()
    if not text:
        raise TaskError("task text cannot be empty")
    tasks = load_tasks()
    task = {
        "id": max((t["id"] for t in tasks), default=0) + 1,
        "text": text,
        "done": False,
        "priority": normalize_priority(priority),
        "due": parse_due(due),
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    tasks.append(task)
    save_tasks(tasks)
    return task


def _find(tasks, task_id):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise TaskError(f"no task with id {task_id}")


def set_done(task_id, done=True):
    tasks = load_tasks()
    task = _find(tasks, task_id)
    task["done"] = bool(done)
    save_tasks(tasks)
    return task


def remove_task(task_id):
    tasks = load_tasks()
    task = _find(tasks, task_id)
    tasks.remove(task)
    save_tasks(tasks)
    return task


def clear_tasks():
    save_tasks([])


# --------------------------------------------------------------------------- #
# Querying (search / filter / sort)
# --------------------------------------------------------------------------- #

def is_overdue(task):
    due = task.get("due")
    if not due or task.get("done"):
        return False
    try:
        return date.fromisoformat(due) < date.today()
    except ValueError:
        return False

def due_status(task):
    """Return '', 'overdue', or 'today' for display styling."""
    due = task.get("due")
    if not due:
        return ""
    try:
        d = date.fromisoformat(due)
    except ValueError:
        return ""
    if not task.get("done") and d < date.today():
        return "overdue"
    if d == date.today():
        return "today"
    return ""


def _matches(task, *, status, priority, overdue, keyword):
    if status == "pending" and task.get("done"):
        return False
    if status == "done" and not task.get("done"):
        return False
    if priority and task.get("priority", "medium") != priority:
        return False
    if overdue and not is_overdue(task):
        return False
    if keyword and keyword.lower() not in task.get("text", "").lower():
        return False
    return True


def _sort_key(task, mode):
    done = task.get("done", False)
    if mode == "due":
        return (done, task.get("due") or "9999-12-31")
    if mode == "none":
        return (done, task.get("id", 0))
    return (done, PRIORITY_RANK.get(task.get("priority", "medium"), 1))  # "priority"


def query(*, status="all", priority=None, overdue=False, keyword=None, sort="priority"):
    """Return tasks matching the filters, sorted for display."""
    tasks = [
        t for t in load_tasks()
        if _matches(t, status=status, priority=priority, overdue=overdue, keyword=keyword)
    ]
    tasks.sort(key=lambda t: _sort_key(t, sort))
    return tasks
