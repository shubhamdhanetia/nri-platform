from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.dependencies import get_current_user
from app.core.ride_time import utc_now_naive
from app.db.dependencies import get_db
from app.models.housing import HousingInquiry, HousingMessage, HousingPost, HousingReport, HousingSave
from app.models.user import User
from app.services.location_search import resolve_post_location
from app.services.post_search import h3_cells_for_bounds
from app.schemas.housing import (
    HousingCollection, HousingInput, HousingInquiryCollection, HousingInquiryResponse,
    HousingMember, HousingMessageInput, HousingMessageResponse, HousingReportInput,
    HousingReportResponse, HousingResponse, HousingSearch, HousingStatusInput,
    HousingVisibilityInput, Status,
)

router = APIRouter()


def accessible_post(db: Session, post_id: UUID, user: User, *, owner_only: bool = False, lock: bool = False) -> HousingPost:
    statement = select(HousingPost).where(HousingPost.id == post_id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    post = db.scalar(statement)
    if post is None or (owner_only and post.owner_id != user.id) or (post.is_private and post.owner_id != user.id):
        raise HTTPException(404, "Housing post not found.")
    return post


def require_available(post: HousingPost) -> None:
    now = utc_now_naive()
    if post.status != "ACTIVE" or post.expires_at <= now or (post.available_until is not None and post.available_until < now.date()):
        raise HTTPException(409, "This housing post is no longer available for new inquiries.")


def response_for(db: Session, post: HousingPost, user: User) -> HousingResponse:
    response = HousingResponse.model_validate(post)
    response.my_saved = db.get(HousingSave, (user.id, post.id)) is not None
    return response


def collection_for(db: Session, posts: list[HousingPost], user: User, limit: int) -> HousingCollection:
    visible = posts[:limit]
    saved = set(db.scalars(select(HousingSave.housing_id).where(
        HousingSave.user_id == user.id, HousingSave.housing_id.in_([post.id for post in visible]),
    ))) if visible else set()
    responses = []
    for post in visible:
        response = HousingResponse.model_validate(post)
        response.my_saved = post.id in saved
        responses.append(response)
    return HousingCollection(items=responses, has_more=len(posts) > limit)


def effective_expired():
    now = utc_now_naive()
    return or_(HousingPost.expires_at <= now, and_(HousingPost.available_until.is_not(None), HousingPost.available_until < now.date()))


@router.post("/search", response_model=HousingCollection)
def search_housing(payload: HousingSearch, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    statement = select(HousingPost).options(joinedload(HousingPost.owner)).where(
        HousingPost.status == "ACTIVE", HousingPost.is_private.is_(False), ~effective_expired(),
    )
    if payload.bounds is not None:
        bounds = payload.bounds
        cells = h3_cells_for_bounds(bounds)
        statement = statement.where(
            HousingPost.h3_cell_id.in_(cells),
            HousingPost.latitude >= bounds.south,
            HousingPost.latitude <= bounds.north,
        )
        if bounds.east < bounds.west:
            statement = statement.where(or_(HousingPost.longitude >= bounds.west, HousingPost.longitude <= bounds.east))
        else:
            statement = statement.where(HousingPost.longitude >= bounds.west, HousingPost.longitude <= bounds.east)
    if payload.view == "PLACES":
        statement = statement.where(HousingPost.kind == "LISTING")
    else:
        statement = statement.where(HousingPost.kind.in_(("REQUEST", "TOGETHER")))
        if payload.kind:
            statement = statement.where(HousingPost.kind == payload.kind)
    for key in ("room_type", "arrangement", "stay_type", "currency", "price_period", "furnishing", "bathroom", "kitchen", "parking", "laundry"):
        value = getattr(payload, key)
        if value is not None:
            statement = statement.where(getattr(HousingPost, key) == value)
    if payload.city:
        city = payload.city.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(HousingPost.city.ilike(city, escape="\\"))
    if payload.query:
        keyword = "%" + payload.query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(
            HousingPost.title.ilike(keyword, escape="\\"), HousingPost.description.ilike(keyword, escape="\\"),
            HousingPost.area.ilike(keyword, escape="\\"), HousingPost.city.ilike(keyword, escape="\\"),
            HousingPost.location.ilike(keyword, escape="\\"),
        ))
    if payload.min_amount is not None:
        statement = statement.where(HousingPost.amount >= payload.min_amount)
    if payload.max_amount is not None:
        statement = statement.where(HousingPost.amount <= payload.max_amount)
    if payload.available_from:
        statement = statement.where(
            HousingPost.available_from <= payload.available_from,
            or_(HousingPost.available_until.is_(None), HousingPost.available_until >= payload.available_from),
        )
    if payload.available_until:
        statement = statement.where(
            HousingPost.available_from <= payload.available_until,
            or_(HousingPost.available_until.is_(None), HousingPost.available_until >= payload.available_until),
        )
    if payload.available_from and payload.available_until:
        statement = statement.where(HousingPost.minimum_stay_days <= (payload.available_until - payload.available_from).days + 1)
    posts = list(db.scalars(statement.order_by(HousingPost.created_at.desc(), HousingPost.id.desc())
                            .offset(payload.offset).limit(payload.limit + 1)))
    return collection_for(db, posts, user, payload.limit)


@router.get("/me", response_model=HousingCollection)
def my_housing(
    status: Status | None = None, expired: bool | None = None,
    limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0, le=10000),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    statement = select(HousingPost).options(joinedload(HousingPost.owner)).where(HousingPost.owner_id == user.id)
    if status:
        statement = statement.where(HousingPost.status == status)
    if expired is not None:
        statement = statement.where(effective_expired() if expired else ~effective_expired())
    posts = list(db.scalars(statement.order_by(HousingPost.created_at.desc(), HousingPost.id.desc()).offset(offset).limit(limit + 1)))
    return collection_for(db, posts, user, limit)


@router.get("/saved", response_model=HousingCollection)
def saved_housing(
    limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0, le=10000),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    posts = list(db.scalars(select(HousingPost).options(joinedload(HousingPost.owner)).join(HousingSave).where(
        HousingSave.user_id == user.id, or_(HousingPost.is_private.is_(False), HousingPost.owner_id == user.id),
    ).order_by(HousingSave.created_at.desc(), HousingPost.id.desc()).offset(offset).limit(limit + 1)))
    return collection_for(db, posts, user, limit)


def inquiry_response(inquiry: HousingInquiry) -> HousingInquiryResponse:
    return HousingInquiryResponse(
        id=inquiry.id, housing_id=inquiry.housing_id, housing_title=inquiry.housing.title,
        sender=HousingMember.model_validate(inquiry.sender), owner=HousingMember.model_validate(inquiry.housing.owner),
        created_at=inquiry.created_at, messages=[HousingMessageResponse.model_validate(message) for message in inquiry.messages],
    )


@router.get("/inquiries", response_model=HousingInquiryCollection)
def my_inquiries(
    limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0, le=10000),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    inquiries = list(db.scalars(select(HousingInquiry).join(HousingPost).options(
        selectinload(HousingInquiry.messages), joinedload(HousingInquiry.sender),
        joinedload(HousingInquiry.housing).joinedload(HousingPost.owner),
    ).where(
        or_(HousingInquiry.sender_id == user.id, HousingPost.owner_id == user.id),
        or_(HousingPost.is_private.is_(False), HousingPost.owner_id == user.id),
    ).order_by(HousingInquiry.created_at.desc(), HousingInquiry.id.desc()).offset(offset).limit(limit + 1)))
    return HousingInquiryCollection(items=[inquiry_response(item) for item in inquiries[:limit]], has_more=len(inquiries) > limit)


@router.post("/inquiries/{inquiry_id}/messages", response_model=HousingInquiryResponse)
def reply_to_inquiry(inquiry_id: UUID, payload: HousingMessageInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inquiry = db.get(HousingInquiry, inquiry_id)
    if inquiry is None:
        raise HTTPException(404, "Inquiry not found.")
    post = accessible_post(db, inquiry.housing_id, user, lock=True)
    if user.id not in (inquiry.sender_id, post.owner_id):
        raise HTTPException(404, "Inquiry not found.")
    inquiry.messages.append(HousingMessage(sender_id=user.id, content=payload.message))
    db.commit()
    return inquiry_response(inquiry)


@router.post("", response_model=HousingResponse, status_code=201)
def create_housing(payload: HousingInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.available_until and payload.available_until < utc_now_naive().date():
        raise HTTPException(422, "Availability cannot end in the past.")
    location = resolve_post_location(payload.location_id)
    post = HousingPost(
        **payload.model_dump(exclude={"location_id"}), **location.model_dump(),
        owner_id=user.id, expires_at=utc_now_naive() + timedelta(days=30),
    )
    db.add(post)
    db.commit()
    return response_for(db, post, user)


@router.get("/{post_id}", response_model=HousingResponse)
def housing_detail(post_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return response_for(db, accessible_post(db, post_id, user), user)


@router.put("/{post_id}", response_model=HousingResponse)
def edit_housing(post_id: UUID, payload: HousingInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = accessible_post(db, post_id, user, owner_only=True, lock=True)
    fields = payload.model_dump(exclude={"location_id"})
    if post.location_id != payload.location_id:
        fields.update(resolve_post_location(payload.location_id).model_dump())
    for key, value in fields.items():
        setattr(post, key, value)
    post.updated_at = utc_now_naive()
    db.commit()
    return response_for(db, post, user)


def renew(post: HousingPost) -> None:
    if post.available_until and post.available_until < utc_now_naive().date():
        raise HTTPException(409, "Update the availability dates before renewing or reopening this post.")
    post.expires_at = utc_now_naive() + timedelta(days=30)


@router.put("/{post_id}/status", response_model=HousingResponse)
def set_status(post_id: UUID, payload: HousingStatusInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = accessible_post(db, post_id, user, owner_only=True, lock=True)
    if payload.status == "ACTIVE":
        renew(post)
    post.status = payload.status
    db.commit()
    return response_for(db, post, user)


@router.post("/{post_id}/renew", response_model=HousingResponse)
def renew_housing(post_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = accessible_post(db, post_id, user, owner_only=True, lock=True)
    if post.status != "ACTIVE":
        raise HTTPException(409, "Reopen the post before renewing availability.")
    renew(post)
    db.commit()
    return response_for(db, post, user)


@router.put("/{post_id}/visibility", response_model=HousingResponse)
def set_visibility(post_id: UUID, payload: HousingVisibilityInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = accessible_post(db, post_id, user, owner_only=True, lock=True)
    post.is_private = payload.is_private
    db.commit()
    return response_for(db, post, user)


@router.put("/{post_id}/saved")
def save_housing(post_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, bool]:
    accessible_post(db, post_id, user, lock=True)
    if db.get(HousingSave, (user.id, post_id)) is None:
        db.add(HousingSave(user_id=user.id, housing_id=post_id))
    db.commit()
    return {"saved": True}


@router.delete("/{post_id}/saved")
def unsave_housing(post_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, bool]:
    accessible_post(db, post_id, user, lock=True)
    db.execute(delete(HousingSave).where(HousingSave.user_id == user.id, HousingSave.housing_id == post_id))
    db.commit()
    return {"saved": False}


@router.post("/{post_id}/inquiries", response_model=HousingInquiryResponse, status_code=201)
def inquire(post_id: UUID, payload: HousingMessageInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = accessible_post(db, post_id, user, lock=True)
    if post.owner_id == user.id:
        raise HTTPException(409, "You cannot inquire on your own housing post.")
    inquiry = db.scalar(select(HousingInquiry).where(HousingInquiry.housing_id == post_id, HousingInquiry.sender_id == user.id))
    if inquiry is None:
        require_available(post)
        inquiry = HousingInquiry(housing_id=post_id, sender_id=user.id)
        db.add(inquiry)
    inquiry.messages.append(HousingMessage(sender_id=user.id, content=payload.message))
    db.commit()
    return inquiry_response(inquiry)


@router.post("/{post_id}/reports", response_model=HousingReportResponse, status_code=201)
def report_housing(post_id: UUID, payload: HousingReportInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = accessible_post(db, post_id, user, lock=True)
    if post.owner_id == user.id:
        raise HTTPException(409, "You cannot report your own housing post.")
    report = db.scalar(select(HousingReport).where(HousingReport.housing_id == post_id, HousingReport.reporter_id == user.id))
    if report is not None:
        raise HTTPException(409, "You have already reported this housing post.")
    report = HousingReport(housing_id=post_id, reporter_id=user.id, **payload.model_dump())
    db.add(report)
    db.commit()
    return HousingReportResponse(id=report.id, detail="Report recorded for review.")


@router.delete("/{post_id}")
def delete_housing(post_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, str]:
    post = accessible_post(db, post_id, user, owner_only=True, lock=True)
    inquiries = select(HousingInquiry.id).where(HousingInquiry.housing_id == post_id)
    db.execute(delete(HousingMessage).where(HousingMessage.inquiry_id.in_(inquiries)))
    db.execute(delete(HousingInquiry).where(HousingInquiry.housing_id == post_id))
    db.execute(delete(HousingSave).where(HousingSave.housing_id == post_id))
    db.execute(delete(HousingReport).where(HousingReport.housing_id == post_id))
    db.delete(post)
    db.commit()
    return {"detail": "Housing post deleted."}
