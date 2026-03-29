from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import DailyTaskEntry, ExecuteRequest, CompleteRequest, CompleteResponse
from app.service.daily_service import get_today_logs, get_daily_plan, execute_task, complete_task
from app.service.user_service import get_or_create_user

router = APIRouter(prefix="/api/v1", tags=["daily"])


@router.get("/daily/{username}", response_model=list[DailyTaskEntry])
def daily_logs(username: str, db: Session = Depends(get_db)):
    """Today's log entries — what has been executed/completed so far."""
    get_or_create_user(db, username)
    logs = get_today_logs(db, username)
    return [
        DailyTaskEntry(
            time=log.task_time,
            activity=log.activity,
            xp=0,
            is_custom=False,
            status=log.status,
            executed_at=log.executed_at,
            completed_at=log.completed_at,
            xp_earned=log.xp_earned,
            time_diff_minutes=log.time_diff_minutes,
            duration_minutes=log.duration_minutes,
        )
        for log in logs
    ]


@router.get("/daily/{username}/plan", response_model=list[DailyTaskEntry])
def daily_plan(username: str, db: Session = Depends(get_db)):
    """Full daily schedule merged with today's execution status."""
    get_or_create_user(db, username)
    plan = get_daily_plan(db, username)
    return [DailyTaskEntry(**entry) for entry in plan]


@router.post("/daily/{username}/execute")
def start_task(username: str, body: ExecuteRequest, db: Session = Depends(get_db)):
    get_or_create_user(db, username)
    return execute_task(db, username, body)


@router.post("/daily/{username}/complete", response_model=CompleteResponse)
def finish_task(username: str, body: CompleteRequest, db: Session = Depends(get_db)):
    get_or_create_user(db, username)
    return complete_task(db, username, body)
