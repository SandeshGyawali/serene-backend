from sqlalchemy.orm import Session
from datetime import date, datetime
from app.models.db_models import DailyLog, Task
from app.models.schemas import ExecuteRequest, CompleteRequest, CompleteResponse
from app.utils.time_utils import get_period, time_diff_minutes, calc_xp, calc_duration_feedback, calc_level
from app.service.user_service import add_xp, get_or_create_user


def get_today_logs(db: Session, username: str) -> list[DailyLog]:
    today = date.today()
    return (
        db.query(DailyLog)
        .filter(DailyLog.username == username, DailyLog.log_date == today)
        .all()
    )


def get_daily_plan(db: Session, username: str) -> list[dict]:
    """Merge task list with today's logs to build the full annotated plan."""
    tasks = db.query(Task).filter(Task.username == username).order_by(Task.time).all()
    today_logs = {log.task_time: log for log in get_today_logs(db, username)}

    result = []
    for t in tasks:
        log = today_logs.get(t.time)
        entry = {
            "time": t.time,
            "activity": t.activity,
            "xp": t.xp,
            "is_custom": t.is_custom,
            "period": get_period(t.time),
            "status": log.status if log else "pending",
            "executed_at": log.executed_at if log else None,
            "completed_at": log.completed_at if log else None,
            "xp_earned": log.xp_earned if log else None,
            "time_diff_minutes": log.time_diff_minutes if log else None,
            "duration_minutes": log.duration_minutes if log else None,
        }
        result.append(entry)
    return result


def execute_task(db: Session, username: str, req: ExecuteRequest) -> dict:
    today = date.today()
    log = (
        db.query(DailyLog)
        .filter(
            DailyLog.username == username,
            DailyLog.log_date == today,
            DailyLog.task_time == req.time,
        )
        .first()
    )

    if log and log.status in ("executing", "completed"):
        return {"status": log.status, "executed_at": log.executed_at}

    now = datetime.utcnow()
    if log:
        log.status = "executing"
        log.executed_at = now
    else:
        log = DailyLog(
            username=username,
            log_date=today,
            task_time=req.time,
            activity=req.activity,
            status="executing",
            executed_at=now,
        )
        db.add(log)

    db.commit()
    db.refresh(log)
    return {"status": "executing", "executed_at": log.executed_at}


def complete_task(db: Session, username: str, req: CompleteRequest) -> CompleteResponse:
    today = date.today()
    log = (
        db.query(DailyLog)
        .filter(
            DailyLog.username == username,
            DailyLog.log_date == today,
            DailyLog.task_time == req.time,
        )
        .first()
    )

    now = datetime.utcnow()
    executed_at = log.executed_at if (log and log.executed_at) else now

    diff = time_diff_minutes(req.time, executed_at, today)
    duration = round((now - executed_at).total_seconds() / 60, 2)
    xp_earned, xp_percent, timing_feedback = calc_xp(req.xp, diff)
    duration_feedback = calc_duration_feedback(duration)

    if log:
        log.status = "completed"
        log.completed_at = now
        log.xp_earned = xp_earned
        log.time_diff_minutes = diff
        log.duration_minutes = duration
        if not log.executed_at:
            log.executed_at = now
    else:
        log = DailyLog(
            username=username,
            log_date=today,
            task_time=req.time,
            activity=req.activity,
            status="completed",
            executed_at=now,
            completed_at=now,
            xp_earned=xp_earned,
            time_diff_minutes=diff,
            duration_minutes=duration,
        )
        db.add(log)

    db.commit()

    # update user xp
    user = add_xp(db, username, xp_earned)
    level = calc_level(user.xp)

    return CompleteResponse(
        status="completed",
        completed_at=now,
        xp_earned=xp_earned,
        xp_base=req.xp,
        xp_percent=xp_percent,
        time_diff_minutes=diff,
        duration_minutes=duration,
        duration_feedback=duration_feedback,
        timing_feedback=timing_feedback,
        xp=user.xp,
        level=level,
    )
