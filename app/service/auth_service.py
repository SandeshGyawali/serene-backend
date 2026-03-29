"""Authentication service — register and login with bcrypt password hashing."""
from sqlalchemy.orm import Session
import bcrypt
from fastapi import HTTPException

from app.models.db_models import User, Task
from app.models.schemas import RegisterRequest, LoginRequest, LoginResponse
from app.utils.time_utils import calc_level
from app.service.user_service import DEFAULT_TASKS


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def register(db: Session, payload: RegisterRequest) -> LoginResponse:
    """Create a new user account. Raises 409 if username is already taken."""
    username = payload.username.strip().lower()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken.")

    user = User(
        username=username,
        name=payload.name,
        email=payload.email,
        password_hash=_hash(payload.password),
        xp=0,
    )
    db.add(user)
    db.flush()

    # Seed default tasks for the new user
    for t, act, xp in DEFAULT_TASKS:
        db.add(Task(username=username, time=t, activity=act, xp=xp, is_custom=False))

    db.commit()
    db.refresh(user)

    return LoginResponse(
        username=user.username,
        name=user.name,
        email=user.email,
        level=calc_level(user.xp),
        xp=user.xp,
    )


def login(db: Session, payload: LoginRequest) -> LoginResponse:
    """Verify credentials and return user info. Raises 401 on bad credentials."""
    username = payload.username.strip().lower()
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Allow login without password for legacy accounts (no hash stored yet)
    if user.password_hash is None:
        # First login — set the password now
        user.password_hash = _hash(payload.password)
        db.commit()
        db.refresh(user)
    elif not _verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    return LoginResponse(
        username=user.username,
        name=user.name,
        email=user.email,
        level=calc_level(user.xp),
        xp=user.xp,
    )

