from app.service import task_service
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import TaskOut, TaskCreate, TaskUpdate
from app.service.task_service import get_tasks, create_custom_task, update_custom_task, delete_custom_task, undo_planner_changes
from app.service.user_service import get_or_create_user

router = APIRouter(prefix="/api/v1", tags=["tasks"])


@router.get("/tasks/{username}", response_model=list[TaskOut])
def list_tasks(username: str, db: Session = Depends(get_db)):
    get_or_create_user(db, username)
    return get_tasks(db, username)


@router.post("/tasks/{username}/manual", response_model=TaskOut, status_code=201)
def add_custom_task(username: str, body: TaskCreate, db: Session = Depends(get_db)):
    get_or_create_user(db, username)
    return create_custom_task(db, username, body)


@router.put("/tasks/{username}/manual/{time:path}", response_model=TaskOut)
def edit_custom_task(username: str, time: str, body: TaskUpdate, db: Session = Depends(get_db)):
    task = update_custom_task(db, username, time, body)
    if not task:
        raise HTTPException(404, "Custom task not found")
    return task


@router.delete("/tasks/{username}/manual/{time:path}", status_code=204)
def remove_custom_task(username: str, time: str, db: Session = Depends(get_db)):
    deleted = delete_custom_task(db, username, time)
    if not deleted:
        raise HTTPException(404, "Custom task not found")


@router.post("/tasks/{username}/undo-planner")
def undo_planner(username: str, db: Session = Depends(get_db)):
    success = undo_planner_changes(db, username)
    if not success:
        raise HTTPException(404, "No recent planner changes to undo.")
    return {"message": "Undo successful. Tasks restored."}
