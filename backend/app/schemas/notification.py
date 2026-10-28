from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import UTCResponse


class NotificationResponse(UTCResponse):
    id: int
    category: str
    event_type: str
    resource_id: int
    target_path: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationPageResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int
    has_more: bool


class NotificationCountResponse(BaseModel):
    unread_count: int
