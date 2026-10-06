from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLAlchemyEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


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