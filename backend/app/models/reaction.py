from uuid import UUID, uuid4

from enum import Enum

from sqlalchemy import Enum as SQLAlchemyEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PostReactionType(str, Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"


class PostReaction(Base):
    __tablename__ = "post_reactions"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_reactions_post_user"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, index=True)
    post_id: Mapped[UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    reaction: Mapped[PostReactionType] = mapped_column(
        SQLAlchemyEnum(
            PostReactionType,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda reaction_types: [
                reaction_type.value for reaction_type in reaction_types
            ],
            name="post_reaction_type",
        )
    )

    post: Mapped["Post"] = relationship(back_populates="reactions")
    user: Mapped["User"] = relationship(back_populates="post_reactions")
