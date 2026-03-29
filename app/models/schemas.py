from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, Any, List


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str
    name: Optional[str] = None
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    username: str
    name: Optional[str] = None
    email: Optional[str] = None
    level: int = 1
    xp: int = 0


# ── User ─────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    username: str
    level: int
    xp: int
    email: Optional[str] = None
    name: Optional[str] = None

    class Config:
        from_attributes = True


class ProcessStats(BaseModel):
    days: int
    weeks: int
    months: int
    years: int


class ProgressOut(BaseModel):
    streak: int
    total_days_active: int
    total_tasks_completed: int
    history: list = []


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TaskBase(BaseModel):
    time: str
    activity: str
    xp: int = 50
    is_custom: bool = False
    task_source: str = "default"   # "default" | "ai" | "custom"


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    time: Optional[str] = None
    activity: Optional[str] = None
    xp: Optional[int] = None


class TaskOut(TaskBase):
    id: int

    class Config:
        from_attributes = True


# ── Daily ─────────────────────────────────────────────────────────────────────

class DailyTaskEntry(BaseModel):
    time: str
    activity: str
    xp: int
    is_custom: bool
    task_source: str = "default"   # "default" | "ai" | "custom"
    period: Optional[str] = None
    status: str = "pending"
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    xp_earned: Optional[int] = None
    time_diff_minutes: Optional[float] = None
    duration_minutes: Optional[float] = None


class ExecuteRequest(BaseModel):
    time: str
    activity: str
    xp: int = 50
    is_custom: bool = False


class CompleteRequest(BaseModel):
    time: str
    activity: str
    xp: int = 50
    is_custom: bool = False


class CompleteResponse(BaseModel):
    status: str
    completed_at: datetime
    xp_earned: int
    xp_base: int
    xp_percent: float
    time_diff_minutes: float
    duration_minutes: float
    duration_feedback: str
    timing_feedback: str
    xp: int
    level: int


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_input: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    action: Optional[str] = "none"
    actionData: Optional[Any] = None
    response_type: Optional[str] = None
    suggestions: Optional[list] = None
    next_steps_suggestion: Optional[str] = None
    thought_for_reflection: Optional[str] = None
    user_state_reflection: Optional[dict] = None


class HistoryMessageOut(BaseModel):
    id: int
    sender: str
    text: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Completions (OpenAI-compatible) ───────────────────────────────────────────

class CompletionMessage(BaseModel):
    role: str
    content: str


class CompletionRequest(BaseModel):
    messages: list[CompletionMessage]
    conversation_id: Optional[str] = None
    stream: bool = False
    model: Optional[str] = None


# ── Session ───────────────────────────────────────────────────────────────────

class SessionNewResponse(BaseModel):
    conversation_id: str


class SessionEndRequest(BaseModel):
    conversation_id: str


# ── Blog ──────────────────────────────────────────────────────────────────────

class BlogCommentCreate(BaseModel):
    content: str


class BlogCommentOut(BaseModel):
    id: int
    post_id: int
    username: str
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BlogPostCreate(BaseModel):
    title: str
    content: str
    mood: Optional[str] = None
    tags: Optional[List[str]] = None


class BlogPostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    mood: Optional[str] = None
    tags: Optional[List[str]] = None


class BlogPostOut(BaseModel):
    id: int
    username: str
    title: str
    content: str
    mood: Optional[str] = None
    tags: Optional[List[str]] = None
    likes: Optional[List[str]] = None
    like_count: int = 0
    comment_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BlogPostDetail(BlogPostOut):
    comments: List[BlogCommentOut] = []
