"""
Manages per-conversation JSON files stored in local_data/session/ and
custom task JSON files stored in local_data/custom_tasks/.

Session file naming: {session_id}.json
Custom tasks file: local_data/custom_tasks/{username}.json
"""
import json
import os
from datetime import datetime
from pathlib import Path

SESSION_DIR = Path(__file__).resolve().parents[2] / "local_data" / "session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

CUSTOM_TASKS_DIR = Path(__file__).resolve().parents[2] / "local_data" / "custom_tasks"
CUSTOM_TASKS_DIR.mkdir(parents=True, exist_ok=True)


# ── Custom Task JSON helpers ──────────────────────────────────────────────────

def _custom_tasks_path(username: str) -> Path:
    return CUSTOM_TASKS_DIR / f"{username}.json"


def get_custom_tasks(username: str) -> list[dict]:
    """Return all custom tasks for a user from JSON file."""
    path = _custom_tasks_path(username)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def save_custom_task(username: str, task: dict) -> dict:
    """Add or update a custom task in the JSON file (keyed by time)."""
    tasks = get_custom_tasks(username)
    # Replace existing task with same time or append
    updated = False
    for i, t in enumerate(tasks):
        if t.get("time") == task.get("time"):
            tasks[i] = task
            updated = True
            break
    if not updated:
        tasks.append(task)
    _custom_tasks_path(username).write_text(json.dumps(tasks, indent=2, ensure_ascii=False))
    return task


def update_custom_task_json(username: str, original_time: str, updated_task: dict) -> bool:
    """Update an existing custom task identified by original_time."""
    tasks = get_custom_tasks(username)
    for i, t in enumerate(tasks):
        if t.get("time") == original_time:
            tasks[i] = updated_task
            _custom_tasks_path(username).write_text(json.dumps(tasks, indent=2, ensure_ascii=False))
            return True
    return False


def delete_custom_task_json(username: str, time: str) -> bool:
    """Remove a custom task by time from JSON file."""
    tasks = get_custom_tasks(username)
    new_tasks = [t for t in tasks if t.get("time") != time]
    if len(new_tasks) == len(tasks):
        return False  # not found
    _custom_tasks_path(username).write_text(json.dumps(new_tasks, indent=2, ensure_ascii=False))
    return True


def _file_path(session_id: str) -> Path:
    return SESSION_DIR / f"{session_id}.json"


def create_session_file(session_id: str, username: str) -> Path:
    """Create a new empty session JSON file. Called on /session/new."""
    data = {
        "session_id": session_id,
        "username": username,
        "started_at": datetime.utcnow().isoformat(),
        "ended_at": None,
        "messages": [],
    }
    path = _file_path(session_id)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return path


def append_message(session_id: str, sender: str, text: str) -> None:
    """Append a single message to the session file. Silently no-ops if file missing."""
    path = _file_path(session_id)
    if not path.exists():
        return
    data = json.loads(path.read_text())
    data["messages"].append({
        "sender": sender,
        "text": text,
        "timestamp": datetime.utcnow().isoformat(),
    })
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def close_session_file(session_id: str) -> None:
    """Stamp ended_at on the session file. Called on /session/end."""
    path = _file_path(session_id)
    if not path.exists():
        return
    data = json.loads(path.read_text())
    data["ended_at"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def list_sessions(username: str) -> list[dict]:
    """Return summary of all session files for a user, newest first."""
    sessions = []
    for f in sorted(SESSION_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            if data.get("username") == username:
                sessions.append({
                    "session_id": data["session_id"],
                    "started_at": data["started_at"],
                    "ended_at": data["ended_at"],
                    "message_count": len(data.get("messages", [])),
                    "file": f.name,
                })
        except Exception:
            continue
    return sessions


def get_session(session_id: str):
    path = _file_path(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())
