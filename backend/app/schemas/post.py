from datetime import datetime

from pydantic import BaseModel, Field, model_validator

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


class PostSearchBounds(BaseModel):
    north: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    west: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.north <= self.south:
            raise ValueError("north must be greater than south")
        if self.east == self.west or self.east - self.west == -360:
            raise ValueError("longitude bounds must enclose a non-zero area")
        return self


class PostSearchRequest(BaseModel):
    bounds: PostSearchBounds
    limit: int = Field(default=50, ge=1, le=50)
    category: PostCategory | None = None
    post_type: PostType | None = None


class PostSearchResponse(BaseModel):
    posts: list["PostResponse"]
    has_more: bool


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