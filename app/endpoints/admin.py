from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.db_models import User, ConversationAnalysis, ChatMessage
from app.utils.time_utils import calc_level

router = APIRouter(prefix="/api/v1", tags=["admin"])

_ENERGY_ORDER = ["very_low", "low", "neutral", "high", "very_high"]

def _energy_val(e: str) -> int:
    try:
        return _ENERGY_ORDER.index(str(e)) + 1
    except ValueError:
        return 3


@router.get("/stats/mental/{username}")
def user_mental_stats(username: str, db: Session = Depends(get_db)):
    """Per-user mental health stats derived from conversation_analyses."""
    rows = (
        db.query(ConversationAnalysis)
        .filter(ConversationAnalysis.username == username)
        .order_by(ConversationAnalysis.analyzed_at.asc())
        .all()
    )
    if not rows:
        return {"sessions": [], "summary": {}}

    sessions = []
    for r in rows:
        sessions.append({
            "session_id": r.session_id,
            "analyzed_at": r.analyzed_at.isoformat() if r.analyzed_at else None,
            "core_problem": r.core_problem,
            "initial_feelings": r.initial_feelings,
            "initial_energy": r.initial_energy,
            "initial_energy_val": _energy_val(r.initial_energy),
            "final_feelings": r.final_feelings,
            "final_energy": r.final_energy,
            "final_energy_val": _energy_val(r.final_energy),
            "mindset_shift": r.mindset_shift,
            "progress_made": r.progress_made,
            "recommendations": r.recommendations or [],
        })

    # summary
    total = len(sessions)
    improved = sum(1 for s in sessions if s["final_energy_val"] > s["initial_energy_val"])
    avg_start = round(sum(s["initial_energy_val"] for s in sessions) / total, 2)
    avg_end = round(sum(s["final_energy_val"] for s in sessions) / total, 2)

    progress_counts = {}
    for s in sessions:
        p = s["progress_made"] or "unknown"
        progress_counts[p] = progress_counts.get(p, 0) + 1

    # top feelings
    all_feelings = []
    for s in sessions:
        for f in (s["initial_feelings"] or "").split(","):
            f = f.strip().lower()
            if f:
                all_feelings.append(f)
    feeling_counts = {}
    for f in all_feelings:
        feeling_counts[f] = feeling_counts.get(f, 0) + 1
    top_feelings = sorted(feeling_counts.items(), key=lambda x: -x[1])[:8]

    return {
        "sessions": sessions,
        "summary": {
            "total_sessions": total,
            "sessions_improved": improved,
            "avg_start_energy": avg_start,
            "avg_end_energy": avg_end,
            "energy_lift": round(avg_end - avg_start, 2),
            "progress_breakdown": progress_counts,
            "top_feelings": [{"feeling": f, "count": c} for f, c in top_feelings],
        },
    }


@router.get("/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        msg_count = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.username == u.username
        ).scalar() or 0
        analyses_count = db.query(func.count(ConversationAnalysis.id)).filter(
            ConversationAnalysis.username == u.username
        ).scalar() or 0
        result.append({
            "username": u.username,
            "email": u.email,
            "name": u.name,
            "xp": u.xp,
            "level": calc_level(u.xp),
            "created_at": u.created_at,
            "total_messages": msg_count,
            "total_analyses": analyses_count,
        })
    return result


@router.get("/admin/analyses")
def get_all_analyses(db: Session = Depends(get_db)):
    rows = (
        db.query(ConversationAnalysis)
        .order_by(ConversationAnalysis.analyzed_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "session_id": r.session_id,
            "username": r.username,
            "analyzed_at": r.analyzed_at,
            "core_problem": r.core_problem,
            "initial_feelings": r.initial_feelings,
            "initial_energy": r.initial_energy,
            "final_feelings": r.final_feelings,
            "final_energy": r.final_energy,
            "mindset_shift": r.mindset_shift,
            "progress_made": r.progress_made,
            "recommendations": r.recommendations or [],
        }
        for r in rows
    ]


@router.get("/admin/stats")
def get_stats(db: Session = Depends(get_db)):
    total_users = db.query(func.count(User.username)).scalar() or 0
    total_messages = db.query(func.count(ChatMessage.id)).scalar() or 0
    total_analyses = db.query(func.count(ConversationAnalysis.id)).scalar() or 0

    progress_counts = (
        db.query(ConversationAnalysis.progress_made, func.count(ConversationAnalysis.id))
        .group_by(ConversationAnalysis.progress_made)
        .all()
    )
    energy_shifts = db.query(
        ConversationAnalysis.initial_energy,
        ConversationAnalysis.final_energy,
    ).all()

    improved = sum(
        1 for i, f in energy_shifts
        if _energy_rank(f) > _energy_rank(i)
    )

    return {
        "total_users": total_users,
        "total_messages": total_messages,
        "total_analyses": total_analyses,
        "improved_energy": improved,
        "progress_breakdown": {k: v for k, v in progress_counts},
    }


_ENERGY_ORDER = ["very_low", "low", "neutral", "high", "very_high"]

def _energy_rank(val: str) -> int:
    try:
        return _ENERGY_ORDER.index(str(val))
    except ValueError:
        return 2  # neutral default
