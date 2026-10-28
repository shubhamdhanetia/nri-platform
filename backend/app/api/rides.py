from datetime import date, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.repositories import ride_repository as repo
from app.schemas.ride import (
    CancellationInput, ConfirmationInput, DriverProfileInput, DriverProfileResponse,
    RideDetailResponse, RideOfferInput, RideRequestInput, RideRequestResponse,
    RideMapSearchInput, RideMapSearchResponse,
    RideTableSearchInput, RideTableSearchResponse, RideSearchCursor,
)
from app.services import rides
from app.services.location_search import resolve_post_location
from app.services.post_search import h3_cells_for_bounds
from app.services.ride_search import pickup_radius_cells

router = APIRouter()


@router.get("/driver-profile", response_model=DriverProfileResponse | None)
def get_driver(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return repo.driver_profile(db, user.id)


@router.put("/driver-profile", response_model=DriverProfileResponse)
def put_driver(data: DriverProfileInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return rides.save_driver(db, user.id, data)


@router.post("/requests", response_model=RideRequestResponse, status_code=201)
def create(data: RideRequestInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return rides.request_response(db, rides.create_request(db, user.id, data), user.id)


@router.get("/requests", response_model=list[RideRequestResponse])
def browse(
    offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50),
    pickup_location_id: str | None = Query(None, min_length=1, max_length=200),
    dropoff_location_id: str | None = Query(None, min_length=1, max_length=200),
    departure_date: date | None = None, radius_km: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    pickup = resolve_post_location(pickup_location_id) if pickup_location_id else None
    dropoff = resolve_post_location(dropoff_location_id) if dropoff_location_id else None
    matches = repo.open_requests(db, user.id, offset, limit, pickup, dropoff, departure_date, radius_km)
    return [rides.request_response(db, ride, user.id) for ride in matches]


@router.get("/mine", response_model=list[RideRequestResponse])
def mine(
    offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    return [rides.request_response(db, ride, user.id) for ride in repo.my_requests(db, user.id, offset, limit)]


@router.post("/requests/search", response_model=RideMapSearchResponse)
def search_map(
    data: RideMapSearchInput, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cells = h3_cells_for_bounds(data.bounds)
    dropoff = resolve_post_location(data.dropoff_location_id) if data.dropoff_location_id else None
    matches = repo.open_requests(
        db, user.id, 0, data.limit + 1, dropoff=dropoff,
        departure_date=data.departure_date, radius_km=data.radius_km,
        bounds=data.bounds, cell_ids=cells,
        pickup_time_from=data.pickup_time_from, pickup_time_to=data.pickup_time_to,
    )
    return RideMapSearchResponse(
        rides=[rides.request_response(db, ride, user.id) for ride in matches[:data.limit]],
        has_more=len(matches) > data.limit,
    )


@router.post("/requests/table-search", response_model=RideTableSearchResponse)
def search_table(
    data: RideTableSearchInput, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pickup = resolve_post_location(data.pickup_location_id) if data.pickup_location_id else None
    cells = pickup_radius_cells(pickup, data.radius_km) if pickup else None
    matches = repo.table_requests(db, user.id, data, pickup, cells)
    has_more = len(matches) > data.limit
    page = matches[:data.limit]
    return RideTableSearchResponse(
        rides=[rides.request_response(db, ride, user.id) for ride in page],
        has_more=has_more,
        next_cursor=RideSearchCursor(
            pickup_start=page[-1].pickup_start.replace(tzinfo=timezone.utc), id=page[-1].id,
        ) if has_more else None,
    )


@router.get("/requests/{request_id}", response_model=RideDetailResponse)
def get_detail(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return rides.detail(db, rides.get_request(db, request_id, user.id), user.id)


@router.post("/requests/{request_id}/offers", response_model=RideDetailResponse, status_code=201)
def offer(request_id: int, data: RideOfferInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rides.send_offer(db, request_id, user.id, data)
    return get_detail(request_id, db, user)


@router.post("/requests/{request_id}/offers/{offer_id}/withdraw", response_model=RideDetailResponse)
def withdraw(request_id: int, offer_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rides.withdraw_offer(db, request_id, offer_id, user.id)
    return get_detail(request_id, db, user)


@router.post("/requests/{request_id}/confirm", response_model=RideDetailResponse)
def confirm(request_id: int, data: ConfirmationInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rides.confirm(db, request_id, data.offer_id, user.id)
    return get_detail(request_id, db, user)


@router.post("/requests/{request_id}/cancel", response_model=RideDetailResponse)
def cancel(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rides.cancel_request(db, request_id, user.id)
    return get_detail(request_id, db, user)


@router.post("/requests/{request_id}/booking/cancel", response_model=RideDetailResponse)
def cancel_booking(request_id: int, data: CancellationInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rides.change_booking(db, request_id, user.id, reason=data.reason)
    return get_detail(request_id, db, user)


@router.post("/requests/{request_id}/booking/complete", response_model=RideDetailResponse)
def complete(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rides.change_booking(db, request_id, user.id)
    return get_detail(request_id, db, user)
