"""Blog service — CRUD for posts, comments, and likes."""
from sqlalchemy.orm import Session
from app.models.db_models import BlogPost, BlogComment
from app.models.schemas import BlogPostCreate, BlogPostUpdate, BlogCommentCreate


# ── Posts ─────────────────────────────────────────────────────────────────────

def list_posts(db: Session, skip: int = 0, limit: int = 50):
    posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).offset(skip).limit(limit).all()
    return [_enrich(db, p) for p in posts]


def get_post(db: Session, post_id: int):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        return None
    enriched = _enrich(db, post)
    enriched["comments"] = _get_comments(db, post_id)
    return enriched


def create_post(db: Session, username: str, payload: BlogPostCreate):
    post = BlogPost(
        username=username,
        title=payload.title,
        content=payload.content,
        mood=payload.mood,
        tags=payload.tags or [],
        likes=[],
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return _enrich(db, post)


def update_post(db: Session, username: str, post_id: int, payload: BlogPostUpdate):
    post = db.query(BlogPost).filter(BlogPost.id == post_id, BlogPost.username == username).first()
    if not post:
        return None
    if payload.title is not None:
        post.title = payload.title
    if payload.content is not None:
        post.content = payload.content
    if payload.mood is not None:
        post.mood = payload.mood
    if payload.tags is not None:
        post.tags = payload.tags
    db.commit()
    db.refresh(post)
    return _enrich(db, post)


def delete_post(db: Session, username: str, post_id: int) -> bool:
    post = db.query(BlogPost).filter(BlogPost.id == post_id, BlogPost.username == username).first()
    if not post:
        return False
    # Delete comments first (SQLite may not cascade automatically)
    db.query(BlogComment).filter(BlogComment.post_id == post_id).delete()
    db.delete(post)
    db.commit()
    return True


# ── Likes ─────────────────────────────────────────────────────────────────────

def toggle_like(db: Session, post_id: int, username: str):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        return None
    likes = list(post.likes or [])
    if username in likes:
        likes.remove(username)
    else:
        likes.append(username)
    post.likes = likes
    db.commit()
    db.refresh(post)
    return _enrich(db, post)


# ── Comments ──────────────────────────────────────────────────────────────────

def add_comment(db: Session, post_id: int, username: str, payload: BlogCommentCreate):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        return None
    comment = BlogComment(post_id=post_id, username=username, content=payload.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, username: str, comment_id: int) -> bool:
    comment = db.query(BlogComment).filter(
        BlogComment.id == comment_id,
        BlogComment.username == username,
    ).first()
    if not comment:
        return False
    db.delete(comment)
    db.commit()
    return True


# ── Internal helpers ──────────────────────────────────────────────────────────

def _enrich(db: Session, post: BlogPost) -> dict:
    comment_count = db.query(BlogComment).filter(BlogComment.post_id == post.id).count()
    likes = list(post.likes or [])
    return {
        "id": post.id,
        "username": post.username,
        "title": post.title,
        "content": post.content,
        "mood": post.mood,
        "tags": post.tags or [],
        "likes": likes,
        "like_count": len(likes),
        "comment_count": comment_count,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }


def _get_comments(db: Session, post_id: int) -> list:
    return db.query(BlogComment).filter(BlogComment.post_id == post_id).order_by(BlogComment.created_at.asc()).all()

