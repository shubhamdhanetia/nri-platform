from sqlalchemy.orm import Session

from app.models.post import Post, PostCategory, PostType


def create_post(
    db: Session,
    title: str,
    description: str,
    category: PostCategory,
    post_type: PostType,
    city: str,
    user_id: int
):
    post = Post(
        title=title,
        description=description,
        category=category,
        post_type=post_type,
        city=city,
        user_id=user_id
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return post


def update_post(
    db: Session,
    post_id: int,
    user_id: int,
    title: str,
    description: str,
    category: PostCategory,
    post_type: PostType,
    city: str
) -> Post | None:
    post = (
        db.query(Post)
        .filter(
            Post.id == post_id,
            Post.user_id == user_id
        )
        .first()
    )
    if post is None:
        return None

    post.title = title
    post.description = description
    post.category = category
    post.post_type = post_type
    post.city = city
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


def delete_post(
    db: Session,
    post_id: int,
    user_id: int
) -> bool:
    post = (
        db.query(Post)
        .filter(
            Post.id == post_id,
            Post.user_id == user_id
        )
        .first()
    )
    if post is None:
        return False

    db.delete(post)
    db.commit()
    return True