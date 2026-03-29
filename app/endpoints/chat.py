from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import ChatRequest, ChatResponse, HistoryMessageOut
from app.models.db_models import ChatMessage, ConversationAnalysis
from app.service.user_service import get_or_create_user, get_user_level, get_progress
from app.service.task_service import get_tasks
from app.service.oracle_service import ask_oracle
from app.service import session_file_service as sfs
from app.service.analysis_service import analyze_session

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
    file: UploadFile = File(...),
    duration_seconds: str = Form("0"),
    conversation_id: str = Form(None),
    db: Session = Depends(get_db),
):
    from app.core.config import get_settings
    import openai, tempfile, os

    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)
    audio_bytes = await file.read()

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=f, response_format="text")
        transcribed_text = transcript.strip() if isinstance(transcript, str) else str(transcript)
    except Exception as e:
        transcribed_text = f"[Audio transcription unavailable: {e}]"
    finally:
        os.unlink(tmp_path)

    user = get_or_create_user(db, username)
    level = get_user_level(user)
    tasks = [{"time": t.time, "activity": t.activity, "xp": t.xp} for t in get_tasks(db, username)]
    progress = get_progress(db, username)

    history = _get_session_history(db, conversation_id)

    _save_msg(db, username, "user", transcribed_text, session_id=conversation_id)
    if conversation_id:
        sfs.append_message(conversation_id, "user", transcribed_text)

    result = ask_oracle(
        user_input=transcribed_text,
        username=username,
        user_xp=user.xp,
        level=level,
        tasks=tasks,
        streak=progress["streak"],
        history=history,
    )

    ai_message = result.get("message", "")
    _save_msg(db, username, "serene", ai_message, session_id=conversation_id)
    if conversation_id:
        sfs.append_message(conversation_id, "serene", ai_message)

    return {"oracle": result, "transcribed_text": transcribed_text}


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
