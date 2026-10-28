from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.notification import NotificationCountResponse, NotificationPageResponse, NotificationResponse
from app.services import notifications

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
Member = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=NotificationPageResponse)
def inbox(db: DB, user: Member, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)):
    return notifications.inbox(db, user.id, offset, limit)


@router.get("/unread-count", response_model=NotificationCountResponse)
def count(db: DB, user: Member):
    return NotificationCountResponse(unread_count=notifications.unread_count(db, user.id))


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def read(notification_id: int, db: DB, user: Member):
    return notifications.mark_read(db, notification_id, user.id)
