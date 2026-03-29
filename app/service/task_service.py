from typing import Optional
from sqlalchemy.orm import Session
from app.models.db_models import Task, PlannerSnapshot
from app.models.schemas import TaskCreate, TaskUpdate


def get_tasks(db: Session, username: str) -> list:
    return db.query(Task).filter(Task.username == username).order_by(Task.time).all()


def get_task_by_time(db: Session, username: str, time: str) -> Optional[Task]:
    return db.query(Task).filter(Task.username == username, Task.time == time).first()


def save_planner_snapshot(db: Session, username: str):
    """Back up all current tasks for a user before we let the AI optimize them."""
    tasks = db.query(Task).filter(Task.username == username).all()
    tasks_data = [
        {"time": t.time, "activity": t.activity, "xp": t.xp, "is_custom": t.is_custom}
        for t in tasks
    ]
    snapshot = PlannerSnapshot(username=username, tasks_json=tasks_data)
    db.add(snapshot)
    db.commit()


def undo_planner_changes(db: Session, username: str) -> bool:
    """Restores the schedule to its state before the last optimization run."""
    snapshot = db.query(PlannerSnapshot).filter(
        PlannerSnapshot.username == username
    ).order_by(PlannerSnapshot.created_at.desc()).first()

    if not snapshot:
        return False

    # Delete all current tasks for this user
    db.query(Task).filter(Task.username == username).delete()

    # Restore from snapshot data
    for t_data in snapshot.tasks_json:
        task = Task(
            username=username,
            time=t_data["time"],
            activity=t_data["activity"],
            xp=t_data["xp"],
            is_custom=t_data.get("is_custom", False)
        )
        db.add(task)

    # Clean up that snapshot so we don't accidentally undo further back than intended later
    # (Optional: can keep it if we want multi-undo support ladder)
    db.delete(snapshot)
    db.commit()
    return True


def get_task_by_time(db: Session, username: str, time: str) -> Optional[Task]:
    return db.query(Task).filter(Task.username == username, Task.time == time).first()


def create_custom_task(db: Session, username: str, data: TaskCreate) -> Task:  # type: ignore
    task = Task(
        username=username,
        time=data.time,
        activity=data.activity,
        xp=data.xp,
        is_custom=True,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_custom_task(db: Session, username: str, time: str, data: TaskUpdate) -> Optional[Task]:
    task = db.query(Task).filter(
        Task.username == username, Task.time == time
    ).first()
    if not task:
        return None
    if data.time is not None:
        task.time = data.time
    if data.activity is not None:
        task.activity = data.activity
    if data.xp is not None:
        task.xp = data.xp
    db.commit()
    db.refresh(task)
    return task


def delete_custom_task(db: Session, username: str, time: str) -> bool:
    task = db.query(Task).filter(
        Task.username == username, Task.time == time
    ).first()
    if not task:
        return False
    db.delete(task)
    db.commit()
    return True
