from sqlalchemy.orm import Session

from app.models.post import Post


def create_post(
    db: Session,
    title: str,
    description: str,
    category: str,
    city: str,
    user_id: int
):
    post = Post(
        title=title,
        description=description,
        category=category,
        city=city,
        user_id=user_id
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return post


def get_posts(db: Session):
    return (
        db.query(Post)
        .order_by(Post.created_at.desc())
        .all()
    )


def get_posts_by_user(
    db: Session,
    user_id: int
):
    return (
        db.query(Post)
        .filter(Post.user_id == user_id)
        .all()
    )