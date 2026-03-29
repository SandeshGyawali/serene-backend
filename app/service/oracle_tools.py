from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.schemas import TaskCreate, TaskUpdate
from app.models.db_models import ConversationAnalysis
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

    def get_user_analytics(self) -> str:
        """Get summarized long-term mental health analytics and emotional trends for the user. 
        Use this when the user asks about their progress, emotional patterns, or how they have been feeling lately.
        """
        try:
            # Get last 10 session analyses
            rows = (
                self.db.query(ConversationAnalysis)
                .filter(ConversationAnalysis.username == self.username)
                .order_by(ConversationAnalysis.analyzed_at.desc())
                .limit(10)
                .all()
            )
            if not rows:
                return "The user has no recorded session analyses yet."

            summary = []
            for r in rows:
                summary.append(
                    f"- {r.analyzed_at.date() if r.analyzed_at else 'Unknown Date'}: "
                    f"Problem: {r.core_problem}. "
                    f"Feelings: {r.initial_feelings} -> {r.final_feelings}. "
                    f"Progress: {r.progress_made}. "
                    f"Shift: {r.mindset_shift}"
                )
            
            # Brief trends summary
            total = len(summary)
            top_problems = list(set([r.core_problem for r in rows if r.core_problem]))[:3]
            
            return f"""Total sessions analyzed: {total}
Summary of last 10 entries:
{chr(10).join(summary)}

Key recurring themes/problems recently:
{chr(10).join([f"- {p}" for p in top_problems])}"""

        except Exception as e:
            return f"Error fetching analytics: {str(e)}"
            
    def get_tools(self):
        return [self.create_task, self.edit_task, self.delete_task, self.get_user_analytics]
        
    def execute_tool(self, name: str, args: dict) -> str:
        if name == "create_task":
            return self.create_task(**args)
        elif name == "edit_task":
            return self.edit_task(**args)
        elif name == "delete_task":
            return self.delete_task(**args)
        elif name == "get_user_analytics":
            return self.get_user_analytics()
        else:
            return f"Error: Unknown tool {name}"
