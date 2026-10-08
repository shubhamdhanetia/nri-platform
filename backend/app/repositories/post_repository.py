from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.edit_window import EditWindowExpiredError, is_within_edit_window
from app.models.post import Post, PostCategory, PostType
from app.models.reaction import PostReaction, PostReactionType


class PostOwnerReactionError(Exception):
    pass


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
    if not is_within_edit_window(post.created_at):
        raise EditWindowExpiredError

    post.title = title
    post.description = description
    post.category = category
    post.post_type = post_type
    post.city = city
    post.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(post)
    return post


def get_posts(db: Session):
    return (
        db.query(Post)
        .order_by(Post.created_at.desc())
        .all()
    )


def get_post_by_id(db: Session, post_id: int) -> Post | None:
    return (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(Post.id == post_id)
        .first()
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


def get_user_post_reactions(
    db: Session,
    user_id: int,
    post_ids: list[int],
) -> dict[int, PostReactionType]:
    if not post_ids:
        return {}

    reactions = (
        db.query(PostReaction.post_id, PostReaction.reaction)
        .filter(
            PostReaction.user_id == user_id,
            PostReaction.post_id.in_(post_ids),
        )
        .all()
    )
    return {post_id: reaction for post_id, reaction in reactions}


def set_post_reaction(
    db: Session,
    post_id: int,
    user_id: int,
    reaction_type: PostReactionType,
) -> Post | None:
    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .with_for_update()
        .first()
    )
    if post is None:
        return None
    if post.user_id == user_id:
        raise PostOwnerReactionError

    reaction = (
        db.query(PostReaction)
        .filter(
            PostReaction.post_id == post_id,
            PostReaction.user_id == user_id,
        )
        .first()
    )
    if reaction is None:
        reaction = PostReaction(
            post_id=post_id,
            user_id=user_id,
            reaction=reaction_type,
        )
        db.add(reaction)
    else:
        reaction.reaction = reaction_type

    db.commit()
    db.refresh(post)
    return post


def remove_post_reaction(
    db: Session,
    post_id: int,
    user_id: int,
) -> Post | None:
    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .with_for_update()
        .first()
    )
    if post is None:
        return None
    if post.user_id == user_id:
        raise PostOwnerReactionError

    reaction = (
        db.query(PostReaction)
        .filter(
            PostReaction.post_id == post_id,
            PostReaction.user_id == user_id,
        )
        .first()
    )
    if reaction is not None:
        db.delete(reaction)
        db.commit()

    db.refresh(post)
    return post