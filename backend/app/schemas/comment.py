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


class CommentResponse(BaseModel):
    id: int
    content: str
    user_id: int
    post_id: int
    created_at: datetime
    author: PostAuthorResponse

    class Config:
        from_attributes = True
