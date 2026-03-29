"""Blog endpoints — community posts, comments, and likes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.schemas import (
    BlogPostCreate, BlogPostUpdate, BlogPostOut, BlogPostDetail,
    BlogCommentCreate, BlogCommentOut,
)
from app.service import blog_service

router = APIRouter(prefix="/api/v1/blog", tags=["blog"])


# ── Posts ─────────────────────────────────────────────────────────────────────

@router.get("/posts", response_model=List[BlogPostOut])
def list_posts(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Return all blog posts, newest first."""
    return blog_service.list_posts(db, skip=skip, limit=limit)


@router.get("/posts/{post_id}", response_model=BlogPostDetail)
def get_post(post_id: int, db: Session = Depends(get_db)):
    """Return a single post with all its comments."""
    post = blog_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts/{username}", response_model=BlogPostOut, status_code=201)
def create_post(username: str, payload: BlogPostCreate, db: Session = Depends(get_db)):
    """Create a new blog post."""
    return blog_service.create_post(db, username, payload)


@router.put("/posts/{username}/{post_id}", response_model=BlogPostOut)
def update_post(username: str, post_id: int, payload: BlogPostUpdate, db: Session = Depends(get_db)):
    """Edit own post."""
    post = blog_service.update_post(db, username, post_id, payload)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or not yours")
    return post


@router.delete("/posts/{username}/{post_id}")
def delete_post(username: str, post_id: int, db: Session = Depends(get_db)):
    """Delete own post (also removes its comments)."""
    ok = blog_service.delete_post(db, username, post_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Post not found or not yours")
    return {"status": "deleted"}


# ── Likes ─────────────────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/like/{username}", response_model=BlogPostOut)
def toggle_like(post_id: int, username: str, db: Session = Depends(get_db)):
    """Toggle a like on a post. Returns updated post."""
    post = blog_service.toggle_like(db, post_id, username)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


# ── Comments ──────────────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/comments/{username}", response_model=BlogCommentOut, status_code=201)
def add_comment(post_id: int, username: str, payload: BlogCommentCreate, db: Session = Depends(get_db)):
    """Add a comment to a post."""
    comment = blog_service.add_comment(db, post_id, username, payload)
    if not comment:
        raise HTTPException(status_code=404, detail="Post not found")
    return comment


@router.delete("/comments/{username}/{comment_id}")
def delete_comment(username: str, comment_id: int, db: Session = Depends(get_db)):
    """Delete own comment."""
    ok = blog_service.delete_comment(db, username, comment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Comment not found or not yours")
    return {"status": "deleted"}

