#!/usr/bin/env python3
"""Command-line interface for the todo app.

Shares its data layer (store.py) with the Flask web app (app.py), so changes
made in one are visible in the other.

Usage:
    python todo.py add "Buy groceries" --due 2026-06-30 --priority high
    python todo.py list
    python todo.py list --priority high --status pending --overdue --sort due
    python todo.py search milk
    python todo.py done 2
    python todo.py remove 2
    python todo.py clear
"""

import argparse
import sys

import store


def _print_task(number, task, width):
    mark = "x" if task.get("done") else " "
    prio = store.PRIORITY_LABEL.get(task.get("priority", "medium"), "!!").ljust(3)
    line = f"{number:>{width}}. [{mark}] {prio} {task['text']}"
    ds = store.due_status(task)
    if task.get("due"):
        suffix = {"overdue": " OVERDUE", "today": " TODAY"}.get(ds, "")
        line += f" (due {task['due']}{suffix})"
    print(line)


def cmd_add(args):
    try:
        store.add_task(args.text, due=args.due, priority=args.priority)
    except store.TaskError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Added: {args.text}")


def cmd_list(args, keyword=None):
    tasks = store.query(
        status=args.status, priority=args.priority,
        overdue=args.overdue, keyword=keyword if keyword is not None else args.search,
        sort=args.sort,
    )
    if not store.load_tasks():
        print("No tasks yet. Add one with: python todo.py add \"...\"")
        return
    if not tasks:
        print("No tasks match those filters.")
        return
    width = max(len(str(t["id"])) for t in tasks)
    for task in tasks:
        _print_task(task["id"], task, width)


def cmd_search(args):
    tasks = store.query(keyword=args.text, sort="priority")
    if not tasks:
        print("No tasks match.")
        return
    width = max(len(str(t["id"])) for t in tasks)
    for task in tasks:
        _print_task(task["id"], task, width)


def _by_id(task_id, action):
    try:
        return action(task_id)
    except store.TaskError as exc:
        print(f"Error: {exc}. Run 'list' to see task ids.", file=sys.stderr)
        sys.exit(1)


def cmd_done(args):
    task = _by_id(args.id, lambda i: store.set_done(i, True))
    print(f"Done: {task['text']}")


def cmd_remove(args):
    task = _by_id(args.id, store.remove_task)
    print(f"Removed: {task['text']}")


def cmd_clear(args):
    store.clear_tasks()
    print("All tasks cleared.")


def build_parser():
    parser = argparse.ArgumentParser(description="A simple command-line todo app.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add a new task")
    p_add.add_argument("text", help="task description")
    p_add.add_argument("--due", metavar="YYYY-MM-DD", help="due date")
    p_add.add_argument("--priority", "-p", choices=store.PRIORITIES, default="medium",
                       help="priority (default: medium)")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="list tasks (the number shown is the task id)")
    p_list.add_argument("--sort", choices=("priority", "due", "none"), default="priority")
    p_list.add_argument("--status", choices=("all", "pending", "done"), default="all")
    p_list.add_argument("--priority", "-p", choices=store.PRIORITIES, default=None)
    p_list.add_argument("--overdue", action="store_true")
    p_list.add_argument("--search", metavar="TEXT", default=None)
    p_list.set_defaults(func=cmd_list)

    p_search = sub.add_parser("search", help="find tasks by text")
    p_search.add_argument("text", help="text to search for")
    p_search.set_defaults(func=cmd_search)

    p_done = sub.add_parser("done", help="mark a task done (by id)")
    p_done.add_argument("id", type=int, help="task id (from 'list')")
    p_done.set_defaults(func=cmd_done)

    p_remove = sub.add_parser("remove", help="remove a task (by id)")
    p_remove.add_argument("id", type=int, help="task id (from 'list')")
    p_remove.set_defaults(func=cmd_remove)

    p_clear = sub.add_parser("clear", help="remove all tasks")
    p_clear.set_defaults(func=cmd_clear)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
