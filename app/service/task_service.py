from typing import Optional
from sqlalchemy.orm import Session
from app.models.db_models import Task
from app.models.schemas import TaskCreate, TaskUpdate


def get_tasks(db: Session, username: str) -> list:
    return db.query(Task).filter(Task.username == username).order_by(Task.time).all()


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
