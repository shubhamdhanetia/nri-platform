from datetime import datetime

from pydantic import BaseModel, Field

from app.models.post import PostCategory, PostType
from app.models.reaction import PostReactionType


class CreatePostRequest(BaseModel):
    title: str
    description: str
    category: PostCategory
    post_type: PostType
    location_id: str = Field(min_length=1, max_length=200)


class UpdatePostRequest(CreatePostRequest):
    pass


class PostLocationFields(BaseModel):
    city: str
    location_id: str
    location: str
    country_code: str
    postal_code: str
    state: str
    latitude: float
    longitude: float
    h3_cell_id: str


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
    location_id: str
    location: str
    country_code: str
    postal_code: str
    state: str
    latitude: float
    longitude: float
    h3_cell_id: str
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