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

    class Config:
        from_attributes = True