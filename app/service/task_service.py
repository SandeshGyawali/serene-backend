from typing import Optional
from sqlalchemy.orm import Session
from app.models.db_models import Task
from app.models.schemas import TaskCreate, TaskUpdate
from app.service import session_file_service as sfs


def get_tasks(db: Session, username: str) -> list:
    """Return all DB tasks (default + ai) merged with custom tasks from JSON, sorted by time."""
    db_tasks = db.query(Task).filter(Task.username == username).order_by(Task.time).all()
    custom_json = sfs.get_custom_tasks(username)

    # Build a set of times already covered by DB tasks to avoid duplicates
    db_times = {t.time for t in db_tasks}

    # Convert custom JSON tasks into Task-like objects (simple namespace) if not already in DB
    extra_custom = []
    for ct in custom_json:
        if ct.get("time") not in db_times:
            extra_custom.append(_json_to_task_obj(ct, username))

    return list(db_tasks) + extra_custom


def _json_to_task_obj(ct: dict, username: str):
    """Convert a custom-task JSON dict to a Task-compatible object."""
    t = Task.__new__(Task)
    t.id = ct.get("id", 0)
    t.username = username
    t.time = ct.get("time", "12:00")
    t.activity = ct.get("activity", "")
    t.xp = ct.get("xp", 50)
    t.is_custom = True
    t.task_source = "custom"
    return t


def get_task_by_time(db: Session, username: str, time: str) -> Optional[Task]:
    return db.query(Task).filter(Task.username == username, Task.time == time).first()


def replace_ai_tasks(db: Session, username: str, new_tasks: list[dict]) -> list[Task]:
    """
    Delete all existing AI-generated tasks for this user and insert the new ones.
    new_tasks: list of dicts with keys: activity, time, xp
    Returns the newly inserted Task objects.
    """
    # Remove old AI tasks
    db.query(Task).filter(
        Task.username == username, Task.task_source == "ai"
    ).delete(synchronize_session=False)
    db.flush()

    inserted = []
    for t in new_tasks:
        task = Task(
            username=username,
            time=t.get("time", "12:00"),
            activity=t.get("activity", "Task"),
            xp=int(t.get("xp", 50)),
            is_custom=False,
            task_source="ai",
        )
        db.add(task)
        inserted.append(task)

    db.commit()
    for task in inserted:
        db.refresh(task)
    return inserted


def create_custom_task(db: Session, username: str, data: TaskCreate) -> Task:
    """Create a custom task in DB and persist to JSON file."""
    task = Task(
        username=username,
        time=data.time,
        activity=data.activity,
        xp=data.xp,
        is_custom=True,
        task_source="custom",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Persist to JSON
    sfs.save_custom_task(username, {
        "id": task.id,
        "time": task.time,
        "activity": task.activity,
        "xp": task.xp,
        "is_custom": True,
        "task_source": "custom",
    })
    return task


def update_custom_task(db: Session, username: str, time: str, data: TaskUpdate) -> Optional[Task]:
    """Update a custom task in DB and JSON file."""
    task = db.query(Task).filter(
        Task.username == username, Task.time == time, Task.task_source == "custom"
    ).first()
    if not task:
        return None

    original_time = task.time
    if data.time is not None:
        task.time = data.time
    if data.activity is not None:
        task.activity = data.activity
    if data.xp is not None:
        task.xp = data.xp
    db.commit()
    db.refresh(task)

    # Sync to JSON
    sfs.update_custom_task_json(username, original_time, {
        "id": task.id,
        "time": task.time,
        "activity": task.activity,
        "xp": task.xp,
        "is_custom": True,
        "task_source": "custom",
    })
    return task


def delete_custom_task(db: Session, username: str, time: str) -> bool:
    """Delete a custom task from DB and JSON file."""
    task = db.query(Task).filter(
        Task.username == username, Task.time == time, Task.task_source == "custom"
    ).first()
    if not task:
        return False
    db.delete(task)
    db.commit()
    sfs.delete_custom_task_json(username, time)
    return True
