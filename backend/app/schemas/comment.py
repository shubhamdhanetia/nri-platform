from uuid import UUID

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.post import PostAuthorResponse


class CreateCommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, content: str) -> str:
        content = content.strip()
        if not content:
            raise ValueError("Comment content cannot be empty")
        return content


class UpdateCommentRequest(CreateCommentRequest):
    pass


class CommentResponse(BaseModel):
    id: UUID
    content: str
    user_id: UUID
    post_id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    author: PostAuthorResponse

    class Config:
        from_attributes = True
