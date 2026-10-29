from uuid import UUID

from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.edit_window import EditWindowExpiredError, is_within_edit_window
from app.models.post import Post, PostCategory, PostType
from app.models.reaction import PostReaction, PostReactionType
from app.models.saved_post import SavedPost
from app.schemas.post import PostLocationFields, PostSearchBounds


class PostOwnerReactionError(Exception):
    pass


def create_post(
    db: Session,
    title: str,
    description: str,
    category: PostCategory,
    post_type: PostType,
    is_private: bool,
    location: PostLocationFields,
    user_id: UUID
):
    post = Post(
        title=title,
        description=description,
        category=category,
        post_type=post_type,
        is_private=is_private,
        **location.model_dump(),
        user_id=user_id
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return post


def update_post(
    db: Session,
    post_id: UUID,
    user_id: UUID,
    title: str,
    description: str,
    category: PostCategory,
    post_type: PostType,
    is_private: bool | None,
    location: PostLocationFields
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
    if is_private is not None:
        post.is_private = is_private
    for field, value in location.model_dump().items():
        setattr(post, field, value)
    post.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(post)
    return post


def set_post_visibility(
    db: Session,
    post_id: UUID,
    user_id: UUID,
    is_private: bool,
) -> Post | None:
    post = (
        db.query(Post)
        .filter(
            Post.id == post_id,
            Post.user_id == user_id,
        )
        .first()
    )
    if post is None:
        return None

    post.is_private = is_private
    db.commit()
    db.refresh(post)
    return post


def get_posts(db: Session):
    return (
        db.query(Post)
        .filter(Post.is_private.is_(False))
        .order_by(Post.created_at.desc())
        .all()
    )


def get_posts_in_bounds(
    db: Session,
    bounds: PostSearchBounds | None,
    h3_cell_ids: set[str],
    limit: int,
    category: PostCategory | None = None,
    post_type: PostType | None = None,
    offset: int = 0,
    query: str = "",
) -> list[Post]:
    if bounds is not None and not h3_cell_ids:
        return []

    filters = [Post.is_private.is_(False)]
    if bounds is not None:
        filters.extend([
            Post.h3_cell_id.in_(h3_cell_ids),
            Post.latitude >= bounds.south,
            Post.latitude <= bounds.north,
        ])
    if category is not None:
        filters.append(Post.category == category)
    if post_type is not None:
        filters.append(Post.post_type == post_type)
    if query.strip():
        filters.append(or_(
            Post.title.icontains(query.strip(), autoescape=True),
            Post.description.icontains(query.strip(), autoescape=True),
            Post.location.icontains(query.strip(), autoescape=True),
        ))
    if bounds is not None and bounds.east < bounds.west:
        filters.append(
            or_(
                Post.longitude >= bounds.west,
                Post.longitude <= bounds.east,
            )
        )
    elif bounds is not None:
        filters.extend([
            Post.longitude >= bounds.west,
            Post.longitude <= bounds.east,
        ])

    return (
        db.query(Post)
        .filter(*filters)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset(offset)
        .limit(limit + 1)
        .all()
    )


def get_post_by_id(db: Session, post_id: UUID) -> Post | None:
    return (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(Post.id == post_id)
        .first()
    )


def get_posts_by_user(
    db: Session,
    user_id: UUID
):
    return (
        db.query(Post)
        .filter(Post.user_id == user_id)
        .all()
    )


def get_saved_posts(db: Session, user_id: UUID) -> list[Post]:
    return (
        db.query(Post)
        .join(SavedPost, SavedPost.post_id == Post.id)
        .filter(
            SavedPost.user_id == user_id,
            or_(Post.is_private.is_(False), Post.user_id == user_id),
        )
        .order_by(SavedPost.saved_at.desc(), SavedPost.id.desc())
        .all()
    )


def get_user_saved_post_ids(
    db: Session,
    user_id: UUID,
    post_ids: list[UUID],
) -> set[UUID]:
    if not post_ids:
        return set()

    saved_post_ids = (
        db.query(SavedPost.post_id)
        .filter(
            SavedPost.user_id == user_id,
            SavedPost.post_id.in_(post_ids),
        )
        .all()
    )
    return {post_id for (post_id,) in saved_post_ids}


def save_post(db: Session, post_id: UUID, user_id: UUID) -> Post | None:
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return None

    saved_post = (
        db.query(SavedPost)
        .filter(
            SavedPost.post_id == post_id,
            SavedPost.user_id == user_id,
        )
        .first()
    )
    if saved_post is None:
        db.add(SavedPost(post_id=post_id, user_id=user_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            already_saved = (
                db.query(SavedPost)
                .filter(
                    SavedPost.post_id == post_id,
                    SavedPost.user_id == user_id,
                )
                .first()
            )
            if already_saved is None:
                raise

    return post


def unsave_post(db: Session, post_id: UUID, user_id: UUID) -> Post | None:
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return None

    saved_post = (
        db.query(SavedPost)
        .filter(
            SavedPost.post_id == post_id,
            SavedPost.user_id == user_id,
        )
        .first()
    )
    if saved_post is not None:
        db.delete(saved_post)
        db.commit()

    return post


def delete_post(
    db: Session,
    post_id: UUID,
    user_id: UUID
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
    user_id: UUID,
    post_ids: list[UUID],
) -> dict[UUID, PostReactionType]:
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
    post_id: UUID,
    user_id: UUID,
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
    post_id: UUID,
    user_id: UUID,
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