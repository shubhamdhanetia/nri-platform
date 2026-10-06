from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLAlchemyEnum, ForeignKey, String, Text, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db.base import Base
from app.models.comment import Comment

if TYPE_CHECKING:
    from app.models.user import User


class PostCategory(str, Enum):
    HOUSING = "HOUSING"
    RIDES = "RIDES"
    JOBS = "JOBS"
    FOOD = "FOOD"
    EVENTS = "EVENTS"
    IMMIGRATION = "IMMIGRATION"
    MARKETPLACE = "MARKETPLACE"
    GENERAL = "GENERAL"


class PostType(str, Enum):
    OFFER = "OFFER"
    REQUEST = "REQUEST"
    DISCUSSION = "DISCUSSION"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
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

    city: Mapped[str] = mapped_column(
        String(100)
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    author: Mapped["User"] = relationship(
        back_populates="posts"
    )

    comments: Mapped[list[Comment]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan"
    )

    comment_count: Mapped[int] = column_property(
        select(func.count(Comment.id))
        .where(Comment.post_id == id)
        .correlate_except(Comment)
        .scalar_subquery()
    )