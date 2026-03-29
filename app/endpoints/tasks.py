from app.service import task_service
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import TaskOut, TaskCreate, TaskUpdate
from app.service.task_service import get_tasks, create_custom_task, update_custom_task, delete_custom_task
from app.service.user_service import get_or_create_user
from app.service import session_file_service as sfs

router = APIRouter(prefix="/api/v1", tags=["tasks"])


@router.get("/tasks/{username}", response_model=list[TaskOut])
def list_tasks(username: str, db: Session = Depends(get_db)):
    """Return all tasks: default (constitution) + AI-generated + user custom (from JSON)."""
    get_or_create_user(db, username)
    return get_tasks(db, username)


@router.post("/tasks/{username}/manual", response_model=TaskOut, status_code=201)
def add_custom_task(username: str, body: TaskCreate, db: Session = Depends(get_db)):
    """Create a user-custom task. Saved in DB (task_source='custom') and JSON file."""
    get_or_create_user(db, username)
    return create_custom_task(db, username, body)


@router.put("/tasks/{username}/manual/{time:path}", response_model=TaskOut)
def edit_custom_task(username: str, time: str, body: TaskUpdate, db: Session = Depends(get_db)):
    """Edit an existing custom task. Only custom tasks can be edited via this endpoint."""
    task = update_custom_task(db, username, time, body)
    if not task:
        raise HTTPException(404, "Custom task not found or not editable (only user-created tasks can be edited)")
    return task


@router.delete("/tasks/{username}/manual/{time:path}", status_code=204)
def remove_custom_task(username: str, time: str, db: Session = Depends(get_db)):
    """Delete a user-custom task from DB and JSON file."""
    deleted = delete_custom_task(db, username, time)
    if not deleted:
        raise HTTPException(404, "Custom task not found or not deletable (only user-created tasks can be deleted)")


@router.get("/tasks/{username}/custom/json")
def get_custom_tasks_json(username: str):
    """Return the raw custom tasks JSON file content for this user."""
    return sfs.get_custom_tasks(username)
