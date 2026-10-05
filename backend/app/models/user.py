from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
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