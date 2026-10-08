from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.api.dependencies import get_current_user
from app.core.edit_window import EditWindowExpiredError

from app.models.post import Post
from app.models.user import User

from app.schemas.post import (
    CreatePostRequest,
    PostDetailResponse,
    PostReactionRequest,
    PostReactionSummary,
    PostResponse,
    UpdatePostRequest
)
from app.models.reaction import PostReactionType
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
    update_post,
    get_user_post_reactions,
    remove_post_reaction,
    set_post_reaction,
    PostOwnerReactionError,
)
from app.repositories.comment_repository import (
    create_comment,
    delete_comment,
    get_comments_by_post,
    update_comment
)

router = APIRouter()


def _post_responses(
    db: Session,
    posts: list[Post],
    user_id: int,
) -> list[PostResponse]:
    reactions = get_user_post_reactions(
        db,
        user_id,
        [post.id for post in posts],
    )
    return [
        PostResponse.model_validate(post).model_copy(
            update={"my_reaction": reactions.get(post.id)}
        )
        for post in posts
    ]


def _reaction_summary(
    post_id: int,
    post: Post,
    reaction: PostReactionType | None,
) -> PostReactionSummary:
    return PostReactionSummary(
        post_id=post_id,
        like_count=post.like_count,
        dislike_count=post.dislike_count,
        my_reaction=reaction,
    )


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
    response_model=list[PostResponse],
    dependencies=[Depends(get_current_user)]
)
def get_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return _post_responses(db, get_posts(db), user.id)

@router.get(
    "/me",
    response_model=list[PostResponse]
)
def get_my_posts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    posts = get_posts_by_user(
        db,
        user.id
    )
    return _post_responses(db, posts, user.id)


@router.get(
    "/{post_id}",
    response_model=PostDetailResponse,
    dependencies=[Depends(get_current_user)]
)
def get_detail(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    post = get_post_by_id(db, post_id)
    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    reaction = get_user_post_reactions(db, user.id, [post_id]).get(post_id)
    return PostDetailResponse.model_validate(post).model_copy(
        update={"my_reaction": reaction}
    )


@router.put(
    "/{post_id}/reaction",
    response_model=PostReactionSummary,
)
def react_to_post(
    post_id: int,
    request: PostReactionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        post = set_post_reaction(
            db=db,
            post_id=post_id,
            user_id=user.id,
            reaction_type=request.reaction,
        )
    except PostOwnerReactionError as error:
        raise HTTPException(
            status_code=403,
            detail="You cannot react to your own post",
        ) from error
    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )
    reaction = get_user_post_reactions(db, user.id, [post_id]).get(post_id)
    return _reaction_summary(post_id, post, reaction)


@router.delete(
    "/{post_id}/reaction",
    response_model=PostReactionSummary,
)
def clear_post_reaction(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        post = remove_post_reaction(
            db=db,
            post_id=post_id,
            user_id=user.id,
        )
    except PostOwnerReactionError as error:
        raise HTTPException(
            status_code=403,
            detail="You cannot react to your own post",
        ) from error
    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )
    return _reaction_summary(post_id, post, None)


@router.get(
    "/{post_id}/comments",
    response_model=list[CommentResponse],
    dependencies=[Depends(get_current_user)]
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
    try:
        comment = update_comment(
            db=db,
            comment_id=comment_id,
            post_id=post_id,
            user_id=user.id,
            content=request.content
        )
    except EditWindowExpiredError as error:
        raise HTTPException(
            status_code=403,
            detail="Comments can only be edited within 30 minutes of creation"
        ) from error
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
    try:
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
    except EditWindowExpiredError as error:
        raise HTTPException(
            status_code=403,
            detail="Posts can only be edited within 30 minutes of creation"
        ) from error
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