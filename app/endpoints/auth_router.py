"""Auth endpoints — register, login, logout."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import RegisterRequest, LoginRequest, LoginResponse
from app.service import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=LoginResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user account."""
    return auth_service.register(db, payload)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate an existing user."""
    return auth_service.login(db, payload)


@router.post("/logout")
def logout():
    """Stateless logout — frontend clears its own session storage."""
    return {"status": "logged_out"}

