"""
Manages per-conversation JSON files stored in local_data/session/.

File naming: {username}_{YYYYMMDD_HHMMSS}_{short_id}.json
Each file holds the full conversation: metadata + all messages.
"""
import json
import os
from datetime import datetime
from pathlib import Path

SESSION_DIR = Path(__file__).resolve().parents[2] / "local_data" / "session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


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


def append_message(
    session_id: str,
    sender: str,
    text: str,
    *,
    kind: str = "text",
    audio_path: str | None = None,
    duration_seconds: float | int | None = None,
) -> None:
    """Append a single message to the session file. Silently no-ops if file missing."""
    path = _file_path(session_id)
    if not path.exists():
        return
    data = json.loads(path.read_text())
    msg = {
        "sender": sender,
        "text": text,
        "timestamp": datetime.utcnow().isoformat(),
        "kind": kind,
    }
    if audio_path:
        msg["audio_path"] = audio_path
    if duration_seconds is not None:
        try:
            msg["duration_seconds"] = float(duration_seconds)
        except Exception:
            pass
    data["messages"].append(msg)
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
