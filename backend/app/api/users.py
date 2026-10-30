from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.repositories.post_repository import get_public_posts_by_user
from app.schemas.user import (
    MemberPostResponse,
    MemberPostsResponse,
    MemberProfileResponse,
    UpdateProfileRequest,
    UserResponse,
)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def me(
    user: User = Depends(get_current_user)
):
    return user


@router.patch("/me", response_model=UserResponse)
def update_me(
    request: UpdateProfileRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    current_user = db.get(User, user.id)
    if current_user is None:
        raise HTTPException(status_code=404, detail="Member not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=MemberProfileResponse, dependencies=[Depends(get_current_user)])
def member_profile(user_id: UUID, db: Session = Depends(get_db)):
    member = db.get(User, user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return MemberProfileResponse(
        id=member.id,
        name=member.name,
        picture=member.picture,
        member_since=member.created_at.date().replace(day=1),
        bio=member.bio,
        home_city=member.home_city,
        languages=member.languages,
    )


@router.get("/{user_id}/posts", response_model=MemberPostsResponse, dependencies=[Depends(get_current_user)])
def member_posts(
    user_id: UUID,
    limit: int = Query(default=12, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="Member not found")
    posts = get_public_posts_by_user(db, user_id, limit, offset)
    return MemberPostsResponse(
        posts=[MemberPostResponse.model_validate(post) for post in posts[:limit]],
        has_more=len(posts) > limit,
    )