from sqlalchemy.orm import Session
from app.models.schemas import TaskCreate, TaskUpdate
from app.service.task_service import create_custom_task, update_custom_task, delete_custom_task

class TaskOracleTools:
    def __init__(self, db: Session, username: str):
        self.db = db
        self.username = username

    def create_task(self, time: str, activity: str, xp: int = 50) -> str:
        """Create a new task in the user's daily schedule. Use this when the user wants to add a new task.
        Args:
            time: The time of the task in HH:MM format.
            activity: A short description of the task.
            xp: Experience points for completing the task (default 50).
        """
        try:
            req = TaskCreate(time=time, activity=activity, xp=xp, is_custom=True)
            task = create_custom_task(self.db, self.username, req)
            return f"Success: Task '{activity}' created at {time} with {xp} XP."
        except Exception as e:
            return f"Error creating task: {str(e)}"

    def edit_task(self, time: str, new_time: str = None, new_activity: str = None, new_xp: int = None) -> str:
        """Edit an existing task in the user's schedule. Use this when the user wants to change a task's time, activity description, or XP. Provide the original time, and any fields to change.
        Args:
            time: The original time of the task in HH:MM format.
            new_time: The new time in HH:MM format (only if changing).
            new_activity: The new activity description (only if changing).
            new_xp: The new XP value (only if changing).
        """
        try:
            req = TaskUpdate(time=new_time, activity=new_activity, xp=new_xp)
            task = update_custom_task(self.db, self.username, time, req)
            if task:
                return f"Success: Task originally at {time} updated successfully."
            return f"Error: Task at {time} not found."
        except Exception as e:
            return f"Error editing task: {str(e)}"

    def delete_task(self, time: str) -> str:
        """Delete a task from the user's daily schedule. Use this when the user wants to remove or cancel a task.
        Args:
            time: The time of the task to delete in HH:MM format.
        """
        try:
            res = delete_custom_task(self.db, self.username, time)
            if res:
                return f"Success: Task at {time} deleted."
            return f"Error: Task at {time} not found."
        except Exception as e:
            return f"Error deleting task: {str(e)}"
            
    def get_tools(self):
        return [self.create_task, self.edit_task, self.delete_task]
        
    def execute_tool(self, name: str, args: dict) -> str:
        if name == "create_task":
            return self.create_task(**args)
        elif name == "edit_task":
            return self.edit_task(**args)
        elif name == "delete_task":
            return self.delete_task(**args)
        else:
            return f"Error: Unknown tool {name}"
