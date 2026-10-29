from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.post import Post
    from app.models.reaction import PostReaction
    from app.models.saved_post import SavedPost


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        index=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(255)
    )

    picture: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    provider: Mapped[str] = mapped_column(
        String(50)
    )

    provider_id: Mapped[str] = mapped_column(
        String(255),
        unique=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    posts: Mapped[list["Post"]] = relationship(
        back_populates="author"
    )

    comments: Mapped[list["Comment"]] = relationship(
        back_populates="author"
    )

    post_reactions: Mapped[list["PostReaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    saved_posts: Mapped[list["SavedPost"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )