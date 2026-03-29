from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import UserOut, ProcessStats, ProgressOut
from app.service.user_service import get_or_create_user, get_user_level, get_process_stats, get_progress

router = APIRouter(prefix="/api/v1", tags=["user"])


@router.get("/user/{username}", response_model=UserOut)
def get_user(username: str, db: Session = Depends(get_db)):
    user = get_or_create_user(db, username)
    return UserOut(
        username=user.username,
        level=get_user_level(user),
        xp=user.xp,
        email=user.email,
        name=user.name,
    )


@router.get("/stats/process/{username}", response_model=ProcessStats)
def process_stats(username: str):
    return get_process_stats(username)


@router.get("/progress/{username}", response_model=ProgressOut)
def progress(username: str, db: Session = Depends(get_db)):
    get_or_create_user(db, username)  # ensure user exists
    return get_progress(db, username)
