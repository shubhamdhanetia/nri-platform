from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.api.dependencies import get_current_user

from app.models.user import User

from app.schemas.post import (
    CreatePostRequest,
    PostResponse
)

from app.repositories.post_repository import (
    create_post,
    delete_post,
    get_posts,
    get_posts_by_user
)

router = APIRouter()

@router.post(
    "",
    response_model=PostResponse
)
def create(
    request: CreatePostRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return create_post(
        db=db,
        title=request.title,
        description=request.description,
        category=request.category,
        city=request.city,
        user_id=user.id
    )

@router.get(
    "",
    response_model=list[PostResponse]
)
def get_all(
    db: Session = Depends(get_db)
):
    return get_posts(db)

@router.get(
    "/me",
    response_model=list[PostResponse]
)
def get_my_posts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return get_posts_by_user(
        db,
        user.id
    )


@router.delete(
    "/{post_id}"
)
def delete(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if not delete_post(
        db=db,
        post_id=post_id,
        user_id=user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    return {"detail": "Post deleted"}