from uuid import UUID, uuid4

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SQLAlchemyEnum, Float, ForeignKey, String, Text, false, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db.base import Base
from app.models.comment import Comment
from app.models.reaction import PostReaction, PostReactionType

if TYPE_CHECKING:
    from app.models.reaction import PostReaction
    from app.models.saved_post import SavedPost
    from app.models.user import User


class PostCategory(str, Enum):
    HOUSING = "HOUSING"
    RIDES = "RIDES"
    JOBS = "JOBS"
    FOOD = "FOOD"
    EVENTS = "EVENTS"
    IMMIGRATION = "IMMIGRATION"
    MARKETPLACE = "MARKETPLACE"
    MEDICAL_SUPPORT = "MEDICAL_SUPPORT"
    GENERAL = "GENERAL"


class PostType(str, Enum):
    OFFER = "OFFER"
    REQUEST = "REQUEST"
    DISCUSSION = "DISCUSSION"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(255)
    )

    description: Mapped[str] = mapped_column(
        Text
    )

    category: Mapped[PostCategory] = mapped_column(
        SQLAlchemyEnum(
            PostCategory,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda categories: [category.value for category in categories],
            name="post_category"
        )
    )

    post_type: Mapped[PostType] = mapped_column(
        SQLAlchemyEnum(
            PostType,
            length=10,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda post_types: [post_type.value for post_type in post_types],
            name="post_type"
        ),
        default=PostType.OFFER.value,
        server_default=PostType.OFFER.value
    )

    is_private: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    location_id: Mapped[str] = mapped_column(
        String(200)
    )

    location: Mapped[str] = mapped_column(
        Text
    )

    country_code: Mapped[str] = mapped_column(
        String(2)
    )

    postal_code: Mapped[str] = mapped_column(
        String(20)
    )

    state: Mapped[str] = mapped_column(
        String(10)
    )

    city: Mapped[str] = mapped_column(
        String(100)
    )

    latitude: Mapped[float] = mapped_column(
        Float
    )

    longitude: Mapped[float] = mapped_column(
        Float
    )

    h3_cell_id: Mapped[str] = mapped_column(
        String(20),
        index=True
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    author: Mapped["User"] = relationship(
        back_populates="posts"
    )

    comments: Mapped[list[Comment]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan"
    )

    reactions: Mapped[list["PostReaction"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan"
    )

    saved_by: Mapped[list["SavedPost"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan"
    )

    like_count: Mapped[int] = column_property(
        select(func.count(PostReaction.id))
        .where(
            PostReaction.post_id == id,
            PostReaction.reaction == PostReactionType.LIKE
        )
        .correlate_except(PostReaction)
        .scalar_subquery()
    )

    dislike_count: Mapped[int] = column_property(
        select(func.count(PostReaction.id))
        .where(
            PostReaction.post_id == id,
            PostReaction.reaction == PostReactionType.DISLIKE
        )
        .correlate_except(PostReaction)
        .scalar_subquery()
    )

    comment_count: Mapped[int] = column_property(
        select(func.count(Comment.id))
        .where(Comment.post_id == id)
        .correlate_except(Comment)
        .scalar_subquery()
    )