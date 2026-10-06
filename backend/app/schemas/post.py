from pydantic import BaseModel


class CreatePostRequest(BaseModel):
    title: str
    description: str
    category: str
    city: str


class PostResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    city: str
    user_id: int

    class Config:
        from_attributes = True