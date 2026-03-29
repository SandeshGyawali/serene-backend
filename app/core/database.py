from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import db_models  # noqa: F401 — registers all models
    Base.metadata.create_all(bind=engine)
    _run_migrations()


def _run_migrations():
    """Apply lightweight schema migrations for SQLite (no Alembic needed)."""
    with engine.connect() as conn:
        # Add password_hash column to users if missing
        try:
            conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE users ADD COLUMN password_hash TEXT"
                )
            )
            conn.commit()
        except Exception:
            pass  # column already exists

        # Add task_source column if it doesn't already exist
        try:
            conn.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE tasks ADD COLUMN task_source TEXT NOT NULL DEFAULT 'default'"
                )
            )
            conn.commit()
        except Exception:
            pass  # column already exists — safe to ignore

        # Backfill existing rows: is_custom=1 → "custom", else stay "default"
        try:
            conn.execute(
                __import__("sqlalchemy").text(
                    "UPDATE tasks SET task_source = 'custom' WHERE is_custom = 1 AND task_source = 'default'"
                )
            )
            conn.commit()
        except Exception:
            pass

        # Create blog_posts table if it doesn't exist
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS blog_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                mood TEXT,
                tags JSON,
                likes JSON,
                created_at DATETIME DEFAULT (datetime('now')),
                updated_at DATETIME DEFAULT (datetime('now'))
            )
        """))
        conn.commit()

        # Create blog_comments table if it doesn't exist
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS blog_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT (datetime('now'))
            )
        """))
        conn.commit()
