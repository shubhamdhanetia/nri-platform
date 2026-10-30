from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.schemas.notification import NotificationPageResponse, NotificationResponse


def notify(
    db: Session, *, user_id: UUID, category: str, event_type: str,
    resource_id: UUID, target_path: str, message: str,
) -> None:
    if not target_path.startswith("/") or target_path.startswith("//") or "\\" in target_path:
        raise ValueError("Notification targets must be application-relative paths.")
    db.add(Notification(
        user_id=user_id, category=category, event_type=event_type,
        resource_id=resource_id, target_path=target_path, message=message,
    ))


def unread_count(db: Session, user_id: UUID) -> int:
    return db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id, Notification.is_read.is_(False),
    )) or 0


def inbox(
    db: Session, user_id: UUID, offset: int, limit: int, *, category: str | None = None,
) -> NotificationPageResponse:
    query = select(Notification).where(Notification.user_id == user_id)
    unread_query = select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id, Notification.is_read.is_(False),
    )
    if category is not None:
        query = query.where(Notification.category == category)
        unread_query = unread_query.where(Notification.category == category)
    rows = list(db.scalars(query.order_by(
        Notification.created_at.desc(), Notification.id.desc(),
    ).offset(offset).limit(limit + 1)))
    return NotificationPageResponse(
        notifications=[NotificationResponse.model_validate(row) for row in rows[:limit]],
        unread_count=db.scalar(unread_query) or 0, has_more=len(rows) > limit,
    )


def mark_read(db: Session, notification_id: UUID, user_id: UUID, *, category: str | None = None) -> Notification:
    query = select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    if category is not None:
        query = query.where(Notification.category == category)
    row = db.scalar(query)
    if row is None:
        raise HTTPException(404, "Notification not found.")
    row.is_read = True
    db.commit()
    db.refresh(row)
    return row
