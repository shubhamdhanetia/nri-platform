from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None = None
    provider: str

    class Config:
        from_attributes = True