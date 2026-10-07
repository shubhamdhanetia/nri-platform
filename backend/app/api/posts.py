from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.api.dependencies import get_current_user

from app.models.user import User

from app.schemas.post import (
    CreatePostRequest,
    PostDetailResponse,
    PostResponse,
    UpdatePostRequest
)
from app.schemas.comment import (
    CommentResponse,
    CreateCommentRequest,
    UpdateCommentRequest
)

from app.repositories.post_repository import (
    create_post,
    delete_post,
    get_posts,
    get_posts_by_user,
    get_post_by_id,
    update_post
)
from app.repositories.comment_repository import (
    create_comment,
    delete_comment,
    get_comments_by_post,
    update_comment
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
        post_type=request.post_type,
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


@router.get(
    "/{post_id}",
    response_model=PostDetailResponse
)
def get_detail(
    post_id: int,
    db: Session = Depends(get_db)
):
    post = get_post_by_id(db, post_id)
    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    return post


@router.get(
    "/{post_id}/comments",
    response_model=list[CommentResponse]
)
def get_comments(
    post_id: int,
    db: Session = Depends(get_db)
):
    if get_post_by_id(db, post_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    return get_comments_by_post(db, post_id)


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=201
)
def create_post_comment(
    post_id: int,
    request: CreateCommentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if get_post_by_id(db, post_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    return create_comment(
        db=db,
        content=request.content,
        user_id=user.id,
        post_id=post_id
    )


@router.put(
    "/{post_id}/comments/{comment_id}",
    response_model=CommentResponse
)
def update_post_comment(
    post_id: int,
    comment_id: int,
    request: UpdateCommentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if get_post_by_id(db, post_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    comment = update_comment(
        db=db,
        comment_id=comment_id,
        post_id=post_id,
        user_id=user.id,
        content=request.content
    )
    if comment is None:
        raise HTTPException(
            status_code=404,
            detail="Comment not found"
        )
    return comment


@router.delete(
    "/{post_id}/comments/{comment_id}"
)
def delete_post_comment(
    post_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if get_post_by_id(db, post_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    if not delete_comment(
        db=db,
        comment_id=comment_id,
        post_id=post_id,
        user_id=user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Comment not found"
        )
    return {"detail": "Comment deleted"}


@router.put(
    "/{post_id}",
    response_model=PostResponse
)
def update(
    post_id: int,
    request: UpdatePostRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    post = update_post(
        db=db,
        post_id=post_id,
        user_id=user.id,
        title=request.title,
        description=request.description,
        category=request.category,
        post_type=request.post_type,
        city=request.city
    )
    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    return post


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