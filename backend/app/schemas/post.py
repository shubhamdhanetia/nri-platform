from datetime import datetime

from pydantic import BaseModel

from app.models.post import PostCategory, PostType


class CreatePostRequest(BaseModel):
    title: str
    description: str
    category: PostCategory
    post_type: PostType
    city: str


class UpdatePostRequest(CreatePostRequest):
    pass


class PostResponse(BaseModel):
    id: int
    title: str
    description: str
    category: PostCategory
    post_type: PostType
    city: str
    user_id: int
    comment_count: int = 0

    class Config:
        from_attributes = True


class PostAuthorResponse(BaseModel):
    id: int
    name: str
    picture: str | None = None

    class Config:
        from_attributes = True


class PostDetailResponse(PostResponse):
    created_at: datetime
    author: PostAuthorResponse