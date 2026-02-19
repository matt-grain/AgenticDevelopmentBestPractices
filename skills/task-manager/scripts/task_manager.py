#!/usr/bin/env python3
"""CLI that manages Claude Code tasks by reading/writing the same JSON files
in ~/.claude/tasks/<session>/ that the built-in TaskCreate/TaskUpdate tools use.

This allows models without native TaskCreate access (e.g. Opus 4.5) to
create and manage tasks visible in the Claude Code task viewer.

IMPORTANT: Use --session-id with the conversation session ID so the task viewer
can resolve project path, slug, and git branch from the session JSONL.
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from filelock import FileLock

CLAUDE_DIR = Path.home() / ".claude"
TASKS_DIR = CLAUDE_DIR / "tasks"
SESSION_FILE = CLAUDE_DIR / ".current_task_session"

# Global session dir, set by resolve_session()
_session_dir: Path | None = None


def resolve_session(session_id: str | None) -> Path:
    """Return the session directory for the given session ID.

    Priority:
    1. --session-id argument (should be the conversation session ID)
    2. CLAUDE_SESSION_ID environment variable
    3. ~/.claude/.current_task_session file
    4. Generate a new UUID (last resort)
    """
    if not session_id:
        session_id = os.environ.get("CLAUDE_SESSION_ID")

    if not session_id:
        if SESSION_FILE.exists():
            session_id = SESSION_FILE.read_text().strip()

    if not session_id:
        session_id = str(uuid.uuid4())

    # Update .current_task_session to point to this session
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(session_id)

    session_dir = TASKS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    lock_file = session_dir / ".lock"
    if not lock_file.exists():
        lock_file.touch()

    return session_dir


def acquire_lock(session_dir: Path):
    """Acquire a file lock for the session directory."""
    lock_path = session_dir / ".lock"
    lock = FileLock(str(lock_path) + ".flock", timeout=5)
    lock.acquire()
    return lock


def next_id(session_dir: Path) -> int:
    """Get the next task ID from highwatermark, or compute from existing files."""
    hwm_file = session_dir / ".highwatermark"
    if hwm_file.exists():
        try:
            hwm = int(hwm_file.read_text().strip())
        except ValueError:
            hwm = 0
    else:
        hwm = 0

    # Also scan existing files to be safe
    existing_ids = []
    for f in session_dir.glob("*.json"):
        try:
            existing_ids.append(int(f.stem))
        except ValueError:
            pass

    max_existing = max(existing_ids) if existing_ids else 0
    new_id = max(hwm, max_existing) + 1
    hwm_file.write_text(str(new_id))
    return new_id


def load_task(session_dir: Path, task_id: str) -> dict | None:
    """Load a task by ID."""
    task_file = session_dir / f"{task_id}.json"
    if not task_file.exists():
        return None
    return json.loads(task_file.read_text())


def save_task(session_dir: Path, task: dict):
    """Save a task to disk."""
    task_file = session_dir / f"{task['id']}.json"
    task_file.write_text(json.dumps(task, indent=2) + "\n")


def cmd_create(args):
    session_dir = resolve_session(args.session_id)
    lock = acquire_lock(session_dir)
    try:
        task_id = next_id(session_dir)
        task = {
            "id": str(task_id),
            "subject": args.subject,
            "description": args.description or "",
            "activeForm": args.active_form or "",
            "status": "pending",
            "blocks": [],
            "blockedBy": [],
        }
        save_task(session_dir, task)
        print(json.dumps({"ok": True, "message": f"Task #{task_id} created successfully: {args.subject}", "task": task}, indent=2))
    finally:
        lock.release()


def cmd_update(args):
    session_dir = resolve_session(args.session_id)
    lock = acquire_lock(session_dir)
    try:
        task = load_task(session_dir, args.task_id)
        if not task:
            print(json.dumps({"ok": False, "error": f"Task #{args.task_id} not found"}), file=sys.stderr)
            sys.exit(1)

        if args.status == "deleted":
            task_file = session_dir / f"{args.task_id}.json"
            task_file.unlink()
            print(json.dumps({"ok": True, "message": f"Task #{args.task_id} deleted"}))
            return

        if args.status:
            task["status"] = args.status
        if args.subject:
            task["subject"] = args.subject
        if args.description:
            task["description"] = args.description
        if args.active_form:
            task["activeForm"] = args.active_form
        if args.add_blocks:
            for bid in args.add_blocks.split(","):
                bid = bid.strip()
                if bid and bid not in task["blocks"]:
                    task["blocks"].append(bid)
        if args.add_blocked_by:
            for bid in args.add_blocked_by.split(","):
                bid = bid.strip()
                if bid and bid not in task["blockedBy"]:
                    task["blockedBy"].append(bid)

        save_task(session_dir, task)
        print(json.dumps({"ok": True, "message": f"Updated task #{args.task_id}", "task": task}, indent=2))
    finally:
        lock.release()


def cmd_get(args):
    session_dir = resolve_session(args.session_id)
    task = load_task(session_dir, args.task_id)
    if not task:
        print(json.dumps({"ok": False, "error": f"Task #{args.task_id} not found"}), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(task, indent=2))


def cmd_list(args):
    session_dir = resolve_session(args.session_id)
    tasks = []
    for f in sorted(session_dir.glob("*.json"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0):
        try:
            tasks.append(json.loads(f.read_text()))
        except (json.JSONDecodeError, ValueError):
            pass

    if not tasks:
        print(json.dumps({"ok": True, "tasks": [], "message": "No tasks found"}))
        return

    print(json.dumps({"ok": True, "tasks": tasks}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Claude Code task manager CLI")
    parser.add_argument("--session-id", default=None,
                        help="Conversation session ID (use ${CLAUDE_SESSION_ID} from skill context)")
    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = sub.add_parser("create", help="Create a new task")
    p_create.add_argument("--subject", required=True, help="Task title (imperative form)")
    p_create.add_argument("--description", default="", help="Detailed task description")
    p_create.add_argument("--active-form", default="", help="Present continuous form for spinner")
    p_create.set_defaults(func=cmd_create)

    # update
    p_update = sub.add_parser("update", help="Update an existing task")
    p_update.add_argument("task_id", help="Task ID to update")
    p_update.add_argument("--status", choices=["pending", "in_progress", "completed", "deleted"])
    p_update.add_argument("--subject", help="New subject")
    p_update.add_argument("--description", help="New description")
    p_update.add_argument("--active-form", help="New activeForm text")
    p_update.add_argument("--add-blocks", help="Comma-separated task IDs this task blocks")
    p_update.add_argument("--add-blocked-by", help="Comma-separated task IDs blocking this task")
    p_update.set_defaults(func=cmd_update)

    # get
    p_get = sub.add_parser("get", help="Get a task by ID")
    p_get.add_argument("task_id", help="Task ID")
    p_get.set_defaults(func=cmd_get)

    # list
    p_list = sub.add_parser("list", help="List all tasks")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
