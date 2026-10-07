from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.edit_window import EditWindowExpiredError, is_within_edit_window
from app.models.comment import Comment


def create_comment(
    db: Session,
    content: str,
    user_id: int,
    post_id: int
) -> Comment:
    comment = Comment(
        content=content,
        user_id=user_id,
        post_id=post_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comments_by_post(db: Session, post_id: int) -> list[Comment]:
    return (
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )


def update_comment(
    db: Session,
    comment_id: int,
    post_id: int,
    user_id: int,
    content: str
) -> Comment | None:
    comment = (
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(
            Comment.id == comment_id,
            Comment.post_id == post_id,
            Comment.user_id == user_id
        )
        .first()
    )
    if comment is None:
        return None
    if not is_within_edit_window(comment.created_at):
        raise EditWindowExpiredError

    comment.content = content
    comment.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(
    db: Session,
    comment_id: int,
    post_id: int,
    user_id: int
) -> bool:
    comment = (
        db.query(Comment)
        .filter(
            Comment.id == comment_id,
            Comment.post_id == post_id,
            Comment.user_id == user_id
        )
        .first()
    )
    if comment is None:
        return False

    db.delete(comment)
    db.commit()
    return True
