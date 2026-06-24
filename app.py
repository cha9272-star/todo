#!/usr/bin/env python3
"""Flask web app for the todo list.

Local dev:
    pip install -r requirements.txt
    python app.py                       # http://127.0.0.1:5000

Production (Render uses this start command):
    gunicorn app:app --bind 0.0.0.0:$PORT
"""

import os

from flask import Flask, flash, redirect, render_template, request, url_for

import store

app = Flask(__name__)
# In production set SECRET_KEY in the Render dashboard; falls back to a dev value.
app.secret_key = os.environ.get("SECRET_KEY", "dev-todo-secret")

STATUSES = ("all", "pending", "done")
SORTS = ("priority", "due", "none")


@app.route("/")
def index():
    status = request.args.get("status", "all")
    if status not in STATUSES:
        status = "all"
    sort = request.args.get("sort", "priority")
    if sort not in SORTS:
        sort = "priority"
    priority = request.args.get("priority") or None
    if priority not in store.PRIORITIES:
        priority = None
    overdue = request.args.get("overdue") == "1"
    keyword = (request.args.get("q") or "").strip() or None

    tasks = store.query(
        status=status, priority=priority, overdue=overdue, keyword=keyword, sort=sort,
    )
    all_tasks = store.load_tasks()
    counts = {
        "total": len(all_tasks),
        "pending": sum(1 for t in all_tasks if not t.get("done")),
        "done": sum(1 for t in all_tasks if t.get("done")),
        "overdue": sum(1 for t in all_tasks if store.is_overdue(t)),
    }

    return render_template(
        "index.html",
        tasks=tasks,
        counts=counts,
        priorities=store.PRIORITIES,
        priority_label=store.PRIORITY_LABEL,
        due_status=store.due_status,
        filters={"status": status, "sort": sort, "priority": priority or "",
                 "overdue": overdue, "q": keyword or ""},
    )


@app.route("/add", methods=["POST"])
def add():
    try:
        store.add_task(
            request.form.get("text", ""),
            due=request.form.get("due") or None,
            priority=request.form.get("priority", "medium"),
        )
    except store.TaskError as exc:
        flash(str(exc), "error")
    return redirect(_back())


@app.route("/toggle/<int:task_id>", methods=["POST"])
def toggle(task_id):
    try:
        task = store._find(store.load_tasks(), task_id)
        store.set_done(task_id, not task.get("done"))
    except store.TaskError as exc:
        flash(str(exc), "error")
    return redirect(_back())


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    try:
        store.remove_task(task_id)
    except store.TaskError as exc:
        flash(str(exc), "error")
    return redirect(_back())


def _back():
    """Redirect back to the list, preserving the current filters."""
    return request.form.get("next") or request.referrer or url_for("index")


if __name__ == "__main__":
    # Local development only. Render runs gunicorn, which imports `app` directly
    # and never executes this block.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
