from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True, index=True)
    email = Column(String, nullable=True)
    name = Column(String, nullable=True)
    xp = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class Task(Base):
    """Persistent tasks (both life.md defaults and custom)."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True, nullable=False)
    time = Column(String, nullable=False)       # "HH:MM"
    activity = Column(String, nullable=False)
    xp = Column(Integer, default=50)
    is_custom = Column(Boolean, default=False)


class DailyLog(Base):
    """Per-day execution tracking for tasks."""
    __tablename__ = "daily_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True, nullable=False)
    log_date = Column(Date, nullable=False, index=True)
    task_time = Column(String, nullable=False)
    activity = Column(String, nullable=False)
    status = Column(String, default="pending")   # pending | executing | completed
    executed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    xp_earned = Column(Integer, default=0)
    time_diff_minutes = Column(Float, nullable=True)
    duration_minutes = Column(Float, nullable=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True, nullable=False)
    session_id = Column(String, index=True, nullable=True)   # null for legacy rows
    sender = Column(String, nullable=False)      # "user" | "serene"
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"

    conversation_id = Column(String, primary_key=True, index=True)
    username = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)


class ConversationAnalysis(Base):
    """Stores AI-generated metadata from analyzing a completed conversation session."""
    __tablename__ = "conversation_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)   # links to sessions.conversation_id
    username = Column(String, index=True, nullable=False)
    analyzed_at = Column(DateTime, server_default=func.now())

    # What the user was dealing with
    core_problem = Column(Text, nullable=True)

    # Emotional state at the start
    initial_feelings = Column(String, nullable=True)          # comma-separated, e.g. "anxious, overwhelmed"
    initial_energy = Column(String, nullable=True)            # very_low | low | neutral | high | very_high

    # Emotional state at the end
    final_feelings = Column(String, nullable=True)
    final_energy = Column(String, nullable=True)              # very_low | low | neutral | high | very_high

    # Insight & progress
    mindset_shift = Column(Text, nullable=True)
    progress_made = Column(String, nullable=True)             # significant | moderate | slight | none

    # Actionable recommendations stored as a JSON array
    recommendations = Column(JSON, nullable=True)

    # Raw AI response preserved in case schema evolves
    raw_response = Column(JSON, nullable=True)
