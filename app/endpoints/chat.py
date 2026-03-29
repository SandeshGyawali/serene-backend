from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import ChatRequest, ChatResponse, HistoryMessageOut
from app.models.db_models import ChatMessage, ConversationAnalysis
from app.service.user_service import get_or_create_user, get_user_level, get_progress
from app.service.task_service import get_tasks
from app.service.oracle_service import ask_oracle
from app.service import session_file_service as sfs
from app.service.analysis_service import analyze_session

from pathlib import Path
from datetime import datetime
import uuid
import re
import os

router = APIRouter(prefix="/api/v1", tags=["chat"])


def _save_msg(db: Session, username: str, sender: str, text: str, session_id: str = None) -> ChatMessage:
    msg = ChatMessage(username=username, sender=sender, text=text, session_id=session_id)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def _get_session_history(db: Session, session_id: str) -> list:
    """Fetch all messages for a session ordered by time — used as context for the AI."""
    if not session_id:
        return []
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [{"sender": r.sender, "text": r.text} for r in rows]


@router.post("/chat/{username}", response_model=ChatResponse)
def chat(username: str, body: ChatRequest, db: Session = Depends(get_db)):
    user = get_or_create_user(db, username)
    level = get_user_level(user)
    tasks = [{"time": t.time, "activity": t.activity, "xp": t.xp} for t in get_tasks(db, username)]
    progress = get_progress(db, username)

    # fetch all prior messages in this session to give AI full context
    history = _get_session_history(db, body.conversation_id)

    # save user message
    _save_msg(db, username, "user", body.user_input, session_id=body.conversation_id)
    if body.conversation_id:
        sfs.append_message(body.conversation_id, "user", body.user_input)

    result = ask_oracle(
        user_input=body.user_input,
        username=username,
        user_xp=user.xp,
        level=level,
        tasks=tasks,
        streak=progress["streak"],
        history=history,
        db=db,
    )

    ai_message = result.get("message", "")
    _save_msg(db, username, "serene", ai_message, session_id=body.conversation_id)
    if body.conversation_id:
        sfs.append_message(body.conversation_id, "serene", ai_message)

    return ChatResponse(
        message=ai_message,
        action=result.get("action", "none"),
        actionData=result.get("actionData"),
        response_type=result.get("response_type"),
        suggestions=result.get("suggestions"),
        next_steps_suggestion=result.get("next_steps_suggestion"),
        thought_for_reflection=result.get("thought_for_reflection"),
        user_state_reflection=result.get("user_state_reflection"),
    )


@router.post("/voice/{username}")
async def voice(
    username: str,
    request: Request,
    file: UploadFile = File(...),
    duration_seconds: str = Form("0"),
    conversation_id: str = Form(None),
    db: Session = Depends(get_db),
):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(400, "Empty audio upload")

    def _safe_part(val: str, fallback: str) -> str:
        raw = (val or "").strip()
        cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", raw)
        return cleaned or fallback

    audio_root = Path(__file__).resolve().parents[2] / "local_data" / "audio"
    safe_username = _safe_part(username, "user")
    session_part = _safe_part(conversation_id, "no_session")
    user_dir = audio_root / safe_username / session_part
    user_dir.mkdir(parents=True, exist_ok=True)

    original_name = (file.filename or "").strip()
    ext = Path(original_name).suffix.lower()
    if not ext:
        ext = ".webm"

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    audio_filename = f"{stamp}_{short_id}{ext}"
    audio_file_path = user_dir / audio_filename
    audio_file_path.write_bytes(audio_bytes)

    audio_rel_path = f"/media/audio/{safe_username}/{session_part}/{audio_filename}"

    model_name = os.getenv("SERENE_WHISPER_MODEL", "base").strip() or "base"
    try:
        from app.service.stt_whisper import transcribe_audio_file
        transcribed_text = await run_in_threadpool(transcribe_audio_file, str(audio_file_path), model_name)
    except ImportError as e:
        raise HTTPException(500, f"Whisper dependency not installed: {e}")
    except Exception as e:
        raise HTTPException(500, f"Whisper transcription failed: {e}")

    user = get_or_create_user(db, username)
    level = get_user_level(user)
    tasks = [{"time": t.time, "activity": t.activity, "xp": t.xp} for t in get_tasks(db, username)]
    progress = get_progress(db, username)

    history = _get_session_history(db, conversation_id)

    _save_msg(db, username, "user", transcribed_text, session_id=conversation_id)
    if conversation_id:
        sfs.append_message(
            conversation_id,
            "user",
            transcribed_text,
            kind="voice",
            audio_path=audio_rel_path,
            duration_seconds=duration_seconds,
        )

    result = ask_oracle(
        user_input=transcribed_text,
        username=username,
        user_xp=user.xp,
        level=level,
        tasks=tasks,
        streak=progress["streak"],
        history=history,
        db=db,
    )

    ai_message = result.get("message", "")
    _save_msg(db, username, "serene", ai_message, session_id=conversation_id)
    if conversation_id:
        sfs.append_message(conversation_id, "serene", ai_message)

    audio_url = str(request.base_url).rstrip("/") + audio_rel_path
    return {
        "voice": {
            "audio_url": audio_url,
            "duration_seconds": duration_seconds,
            "filename": audio_filename,
        },
        "oracle": result,
        "transcribed_text": transcribed_text,
    }


@router.get("/history/{username}", response_model=list[HistoryMessageOut])
def history(username: str, db: Session = Depends(get_db)):
    get_or_create_user(db, username)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.username == username)
        .order_by(ChatMessage.created_at.asc())
        .limit(200)
        .all()
    )
    return messages


@router.get("/sessions/{username}")
def list_sessions(username: str):
    return sfs.list_sessions(username)


@router.get("/sessions/{username}/{session_id}")
def get_session(username: str, session_id: str):
    data = sfs.get_session(session_id)
    if not data or data.get("username") != username:
        raise HTTPException(404, "Session not found")
    return data


@router.post("/sessions/{username}/{session_id}/analyze")
def analyze_conversation(username: str, session_id: str, db: Session = Depends(get_db)):
    data = sfs.get_session(session_id)
    if not data or data.get("username") != username:
        raise HTTPException(404, "Session not found")

    result = analyze_session(data.get("messages", []))

    existing = db.query(ConversationAnalysis).filter(
        ConversationAnalysis.session_id == session_id
    ).first()
    if existing:
        db.delete(existing)
        db.flush()

    record = ConversationAnalysis(
        session_id=session_id,
        username=username,
        core_problem=result.get("core_problem"),
        initial_feelings=result.get("initial_feelings"),
        initial_energy=result.get("initial_energy"),
        final_feelings=result.get("final_feelings"),
        final_energy=result.get("final_energy"),
        mindset_shift=result.get("mindset_shift"),
        progress_made=result.get("progress_made"),
        recommendations=result.get("recommendations"),
        raw_response=result,
    )
    db.add(record)
    db.commit()
    return result
