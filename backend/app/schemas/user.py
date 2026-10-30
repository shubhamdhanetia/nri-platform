from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models.post import PostCategory, PostType


class ProfileFields(BaseModel):
    bio: Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)] | None = None
    home_city: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    languages: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]] = Field(default_factory=list, max_length=10)

    @field_validator("bio", "home_city")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("languages")
    @classmethod
    def unique_languages(cls, values: list[str]) -> list[str]:
        unique: dict[str, str] = {}
        for value in values:
            unique.setdefault(value.casefold(), value)
        return list(unique.values())


class UpdateProfileRequest(ProfileFields):
    model_config = ConfigDict(extra="forbid")


class MemberProfileResponse(ProfileFields):
    id: UUID
    name: str
    picture: str | None = None
    member_since: date


class MemberPostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    category: PostCategory
    post_type: PostType
    city: str
    created_at: datetime
    comment_count: int


class MemberPostsResponse(BaseModel):
    posts: list[MemberPostResponse]
    has_more: bool


class UserResponse(ProfileFields):
    id: UUID
    email: str
    name: str
    picture: str | None = None
    provider: str
    created_at: datetime

    class Config:
        from_attributes = True