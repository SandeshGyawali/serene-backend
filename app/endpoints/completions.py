"""
OpenAI-compatible /v1/chat/completions with SSE streaming.
Session management: /v1/session/new and /v1/session/end.
"""
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import CompletionRequest, SessionNewResponse, SessionEndRequest
from app.models.db_models import Session as ConvSession, ChatMessage
from app.service.oracle_service import ask_oracle_completion
from app.service import session_file_service as sfs

router = APIRouter(prefix="/v1", tags=["completions"])


def _get_session_history(db: Session, session_id: str) -> list:
    """Fetch all prior messages for this session as role/content dicts for Gemini."""
    if not session_id:
        return []
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {"role": "user" if r.sender == "user" else "assistant", "content": r.text}
        for r in rows
    ]


def _save_msg(db: Session, session_id: str, sender: str, text: str):
    # resolve username from session
    username = "incri"
    if session_id:
        session = db.query(ConvSession).filter(ConvSession.conversation_id == session_id).first()
        if session and session.username:
            username = session.username
    msg = ChatMessage(username=username, sender=sender, text=text, session_id=session_id)
    db.add(msg)
    db.commit()


@router.post("/chat/completions")
async def chat_completions(body: CompletionRequest, db: Session = Depends(get_db)):
    # fetch full session history from DB for context
    history = _get_session_history(db, body.conversation_id)

    # incoming messages from frontend (usually just the latest user message)
    new_messages = [{"role": m.role, "content": m.content} for m in body.messages]

    # build full context: history + new message
    full_messages = history + new_messages

    # save user message to DB
    user_text = next((m["content"] for m in reversed(new_messages) if m["role"] == "user"), None)
    if user_text:
        _save_msg(db, body.conversation_id, "user", user_text)
        if body.conversation_id:
            sfs.append_message(body.conversation_id, "user", user_text)

    # call AI with full context
    text = ask_oracle_completion(full_messages)

    # save AI response to DB
    _save_msg(db, body.conversation_id, "serene", text)
    if body.conversation_id:
        sfs.append_message(body.conversation_id, "serene", text)

    if body.stream:
        async def _stream():
            words = text.split(" ")
            for i, word in enumerate(words):
                chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion.chunk",
                    "created": int(datetime.utcnow().timestamp()),
                    "model": "serene",
                    "choices": [{
                        "index": 0,
                        "delta": {"content": word + (" " if i < len(words) - 1 else "")},
                        "finish_reason": None,
                    }],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            done_chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion.chunk",
                "created": int(datetime.utcnow().timestamp()),
                "model": "serene",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(done_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_stream(), media_type="text/event-stream")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(datetime.utcnow().timestamp()),
        "model": "serene",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@router.post("/session/new", response_model=SessionNewResponse)
def new_session(username: str = "incri", db: Session = Depends(get_db)):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    session_id = f"{username}_{timestamp}_{short_id}"

    session = ConvSession(conversation_id=session_id, username=username)
    db.add(session)
    db.commit()

    sfs.create_session_file(session_id, username)
    return SessionNewResponse(conversation_id=session_id)


@router.post("/session/end")
def end_session(body: SessionEndRequest, db: Session = Depends(get_db)):
    session = db.query(ConvSession).filter(
        ConvSession.conversation_id == body.conversation_id
    ).first()
    if session:
        session.ended_at = datetime.utcnow()
        db.commit()

    sfs.close_session_file(body.conversation_id)
    return {"status": "ended", "conversation_id": body.conversation_id}
