from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.models.db_models import User, DailyLog, Task
from app.utils.time_utils import calc_level

DEFAULT_TASKS = [
    ("05:00", "Wake up & hydrate", 30),
    ("05:15", "Morning meditation", 40),
    ("05:45", "Exercise / workout", 80),
    ("07:00", "Shower & groom", 20),
    ("07:30", "Healthy breakfast", 30),
    ("08:00", "Deep work block #1", 100),
    ("10:00", "Short break & stretch", 20),
    ("10:15", "Deep work block #2", 100),
    ("12:00", "Lunch", 30),
    ("12:30", "Walk / light activity", 40),
    ("13:00", "Deep work block #3", 100),
    ("15:00", "Review & planning", 60),
    ("16:00", "Learning / reading", 70),
    ("18:00", "Dinner", 30),
    ("19:00", "Personal project / side quest", 80),
    ("21:00", "Wind down — no screens", 40),
    ("21:30", "Journal / reflection", 50),
    ("22:00", "Sleep", 30),
]


def get_or_create_user(db: Session, username: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username, xp=0)
        db.add(user)
        db.flush()
        # seed default tasks
        for t, act, xp in DEFAULT_TASKS:
            db.add(Task(username=username, time=t, activity=act, xp=xp, is_custom=False))
        db.commit()
        db.refresh(user)
    return user


def get_user_level(user: User) -> int:
    return calc_level(user.xp)


def add_xp(db: Session, username: str, amount: int) -> User:
    user = get_or_create_user(db, username)
    user.xp = max(0, user.xp + amount)
    db.commit()
    db.refresh(user)
    return user


def get_process_stats(db: Session, username: str) -> dict:
    user = db.query(User).filter(User.username == username).first()
    if user and user.created_at:
        start = user.created_at.date()
    else:
        # fallback: use config date for legacy rows without created_at
        from app.core.config import get_settings
        start = get_settings().process_start
    today = date.today()
    total_days = max(0, (today - start).days)
    return {
        "days": total_days,
        "weeks": total_days // 7,
        "months": total_days // 30,
        "years": total_days // 365,
    }


def get_progress(db: Session, username: str) -> dict:
    # total tasks completed
    total_completed = (
        db.query(func.count(DailyLog.id))
        .filter(DailyLog.username == username, DailyLog.status == "completed")
        .scalar()
        or 0
    )

    # distinct active days
    active_days = (
        db.query(func.count(func.distinct(DailyLog.log_date)))
        .filter(DailyLog.username == username, DailyLog.status == "completed")
        .scalar()
        or 0
    )

    # streak: count consecutive days ending today with at least 1 completed task
    streak = _calc_streak(db, username)

    return {
        "streak": streak,
        "total_days_active": active_days,
        "total_tasks_completed": total_completed,
    }


def _calc_streak(db: Session, username: str) -> int:
    rows = (
        db.query(func.distinct(DailyLog.log_date))
        .filter(DailyLog.username == username, DailyLog.status == "completed")
        .all()
    )
    active_dates = sorted({r[0] for r in rows}, reverse=True)
    if not active_dates:
        return 0

    streak = 0
    check = date.today()
    for d in active_dates:
        if d == check:
            streak += 1
            check = check.replace(day=check.day - 1) if check.day > 1 else check  # simple; use timedelta
            from datetime import timedelta
            check = date.today() - timedelta(days=streak)
        else:
            break
    return streak
