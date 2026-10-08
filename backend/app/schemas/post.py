from datetime import datetime

from pydantic import BaseModel

from app.models.post import PostCategory, PostType
from app.models.reaction import PostReactionType


class CreatePostRequest(BaseModel):
    title: str
    description: str
    category: PostCategory
    post_type: PostType
    city: str


class UpdatePostRequest(CreatePostRequest):
    pass


class PostReactionRequest(BaseModel):
    reaction: PostReactionType


class PostResponse(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    title: str
    description: str
    category: PostCategory
    post_type: PostType
    city: str
    user_id: int
    comment_count: int = 0
    like_count: int = 0
    dislike_count: int = 0
    my_reaction: PostReactionType | None = None

    class Config:
        from_attributes = True


class PostReactionSummary(BaseModel):
    post_id: int
    like_count: int
    dislike_count: int
    my_reaction: PostReactionType | None = None


class PostAuthorResponse(BaseModel):
    id: int
    name: str
    picture: str | None = None

    class Config:
        from_attributes = True


class PostDetailResponse(PostResponse):
    created_at: datetime
    author: PostAuthorResponse