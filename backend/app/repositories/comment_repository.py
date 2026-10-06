from sqlalchemy.orm import Session, joinedload

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
