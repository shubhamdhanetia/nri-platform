from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.repositories import carpool_repository as repo
from app.schemas.carpool import (
    CarpoolCreateInput, CarpoolDetailResponse, CarpoolInboxResponse,
    CarpoolNotificationResponse, CarpoolPageResponse, SeatRequestInput,
)
from app.schemas.ride import CancellationInput
from app.services import carpools, notifications

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
Member = Annotated[User, Depends(get_current_user)]


@router.post("/trips", response_model=CarpoolDetailResponse, status_code=201)
def create(data: CarpoolCreateInput, db: DB, user: Member):
    trip = carpools.create_trip(db, user.id, data)
    return carpools.detail(db, trip.id, user.id)


@router.get("/trips", response_model=CarpoolPageResponse)
def browse(
    db: DB, user: Member,
    offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50),
    pickup_location_id: str | None = Query(None, min_length=1, max_length=200),
    dropoff_location_id: str | None = Query(None, min_length=1, max_length=200),
    departure_date: date | None = None,
    passengers: int = Query(1, ge=1, le=8), radius_km: int = Query(25, ge=1, le=100),
):
    return carpools.browse(db, user.id, offset, limit, pickup_location_id, dropoff_location_id, departure_date, passengers, radius_km)


@router.get("/mine", response_model=CarpoolPageResponse)
def mine(db: DB, user: Member, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)):
    rows = repo.my_trips(db, user.id, offset, limit + 1)
    return CarpoolPageResponse(
        trips=[carpools.trip_response(db, trip, user.id) for trip in rows[:limit]],
        has_more=len(rows) > limit,
    )


@router.get("/inbox", response_model=CarpoolInboxResponse, deprecated=True)
def inbox(db: DB, user: Member, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)):
    page = notifications.inbox(db, user.id, offset, limit, category="carpool")
    return CarpoolInboxResponse(
        notifications=[CarpoolNotificationResponse(
            id=row.id, trip_id=row.resource_id, message=row.message,
            is_read=row.is_read, created_at=row.created_at,
        ) for row in page.notifications],
        unread_count=page.unread_count, has_more=page.has_more,
    )


@router.post("/inbox/{notification_id}/read", response_model=CarpoolNotificationResponse, deprecated=True)
def read_notification(notification_id: int, db: DB, user: Member):
    row = notifications.mark_read(db, notification_id, user.id, category="carpool")
    return CarpoolNotificationResponse(
        id=row.id, trip_id=row.resource_id, message=row.message,
        is_read=row.is_read, created_at=row.created_at,
    )


@router.get("/trips/{trip_id}", response_model=CarpoolDetailResponse)
def detail(trip_id: int, db: DB, user: Member):
    return carpools.detail(db, trip_id, user.id)


@router.post("/trips/{trip_id}/requests", response_model=CarpoolDetailResponse, status_code=201)
def request_seats(trip_id: int, data: SeatRequestInput, db: DB, user: Member):
    carpools.request_seats(db, trip_id, user.id, data)
    return carpools.detail(db, trip_id, user.id)


@router.post("/trips/{trip_id}/requests/{request_id}/accept", response_model=CarpoolDetailResponse)
def accept(trip_id: int, request_id: int, db: DB, user: Member):
    carpools.change_request(db, trip_id, request_id, user.id, "accept")
    return carpools.detail(db, trip_id, user.id)


@router.post("/trips/{trip_id}/requests/{request_id}/decline", response_model=CarpoolDetailResponse)
def decline(trip_id: int, request_id: int, db: DB, user: Member):
    carpools.change_request(db, trip_id, request_id, user.id, "decline")
    return carpools.detail(db, trip_id, user.id)


@router.post("/trips/{trip_id}/requests/{request_id}/cancel", response_model=CarpoolDetailResponse)
def cancel_request(trip_id: int, request_id: int, data: CancellationInput, db: DB, user: Member):
    carpools.change_request(db, trip_id, request_id, user.id, "cancel", data.reason)
    return carpools.detail(db, trip_id, user.id)


@router.post("/trips/{trip_id}/cancel", response_model=CarpoolDetailResponse)
def cancel_trip(trip_id: int, data: CancellationInput, db: DB, user: Member):
    carpools.cancel_trip(db, trip_id, user.id, data.reason)
    return carpools.detail(db, trip_id, user.id)
