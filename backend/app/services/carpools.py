from datetime import date, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ride_time import utc_now_naive
from app.models.carpool import CarpoolSeatRequest, CarpoolTrip, SeatStatus
from app.models.user import User
from app.repositories import carpool_repository as repo
from app.repositories.ride_repository import distance_km
from app.schemas.carpool import (
    CarpoolCreateInput, CarpoolDetailResponse, CarpoolLegInput, CarpoolPageResponse,
    CarpoolTripResponse, SeatRequestInput, SeatRequestResponse, SeatResponseStatus, TripResponseStatus,
)
from app.schemas.post import PostAuthorResponse
from app.services.location_search import resolve_post_location
from app.services.rides import require_driver, utc_naive
from app.services import notifications


def get_trip(db: Session, trip_id: int, *, lock: bool = False) -> CarpoolTrip:
    trip = repo.trip_by_id(db, trip_id, lock=lock)
    if trip is None:
        raise HTTPException(404, "Carpool trip not found.")
    return trip


def ensure_open(trip: CarpoolTrip) -> None:
    if trip.status != "OPEN" or trip.pickup_start <= utc_now_naive():
        raise HTTPException(409, "This trip is cancelled or its departure window has started.")


def ensure_cancellable(trip: CarpoolTrip) -> None:
    if trip.status != "OPEN" or trip.pickup_end <= utc_now_naive():
        raise HTTPException(409, "This trip is cancelled or its departure window has ended.")


def notify(db: Session, user_id: int, trip: CarpoolTrip, event_type: str, message: str) -> None:
    route = f"{trip.pickup['city']} to {trip.dropoff['city']}"
    notifications.notify(
        db, user_id=user_id, category="carpool", event_type=event_type,
        resource_id=trip.id, target_path=f"/rides/carpools/{trip.id}", message=f"{message} ({route})"[:500],
    )


def create_trip(db: Session, user_id: int, data: CarpoolCreateInput) -> CarpoolTrip:
    profile = require_driver(db, user_id)

    def leg(value: CarpoolLegInput, outbound_id: int | None = None) -> CarpoolTrip:
        if value.seats > profile.passenger_capacity:
            raise HTTPException(422, "Available seats exceed your driver profile's passenger capacity.")
        pickup = resolve_post_location(value.pickup_location_id)
        dropoff = resolve_post_location(value.dropoff_location_id)
        if pickup.location_id == dropoff.location_id or (
            pickup.latitude == dropoff.latitude and pickup.longitude == dropoff.longitude
        ):
            raise HTTPException(422, "Pickup and drop-off must be different places.")
        if utc_naive(value.pickup_start) <= utc_now_naive():
            raise HTTPException(422, "Departure must be in the future.")
        return CarpoolTrip(
            driver_id=user_id, outbound_id=outbound_id, pickup=pickup.model_dump(),
            dropoff=dropoff.model_dump(), pickup_start=utc_naive(value.pickup_start),
            pickup_end=utc_naive(value.pickup_end), timezone=value.timezone, seats=value.seats,
            bags_per_person=value.bags_per_person, amount=value.amount, currency=value.currency,
            vehicle=profile.vehicle, notes=value.notes,
        )

    outbound = leg(data.outbound)
    returning = leg(data.return_trip) if data.return_trip else None
    db.add(outbound)
    db.flush()
    if returning:
        returning.outbound_id = outbound.id
        db.add(returning)
    db.commit()
    db.refresh(outbound)
    return outbound


def trip_response(db: Session, trip: CarpoolTrip, user_id: int) -> CarpoolTripResponse:
    linked = repo.linked_trip(db, trip)
    own = repo.seat_requests(db, trip.id, user_id)
    available = repo.available_seats(db, trip)
    status: TripResponseStatus = "CANCELLED" if trip.status == "CANCELLED" else (
        "DEPARTED" if trip.pickup_start <= utc_now_naive() else ("FULL" if available == 0 else "OPEN")
    )
    return CarpoolTripResponse(
        **{key: getattr(trip, key) for key in (
            "id", "driver_id", "pickup", "dropoff", "pickup_start", "pickup_end", "timezone",
            "seats", "bags_per_person", "amount", "currency", "vehicle", "notes",
            "cancellation_reason", "created_at",
        )},
        driver=PostAuthorResponse.model_validate(db.get(User, trip.driver_id)),
        linked_trip_id=linked.id if linked else None, is_return=trip.outbound_id is not None,
        available_seats=available, status=status,
        can_cancel=trip.status == "OPEN" and trip.pickup_end > utc_now_naive(),
        my_request_status=request_status(own[0], trip) if own else None,
    )


def request_status(request: CarpoolSeatRequest, trip: CarpoolTrip) -> SeatResponseStatus:
    if request.status == "PENDING" and trip.pickup_start <= utc_now_naive():
        return "EXPIRED"
    return request.status


def detail(db: Session, trip_id: int, user_id: int) -> CarpoolDetailResponse:
    trip = get_trip(db, trip_id)
    owner = trip.driver_id == user_id
    linked = repo.linked_trip(db, trip)
    requests = []
    for request in repo.seat_requests(db, trip.id, None if owner else user_id):
        contacts_visible = request.status == "CONFIRMED"
        requests.append(SeatRequestResponse(
            **{key: getattr(request, key) for key in (
                "id", "trip_id", "passengers", "bags", "message", "cancellation_reason", "created_at",
            )},
            rider=PostAuthorResponse.model_validate(db.get(User, request.rider_id)),
            status=request_status(request, trip),
            rider_phone=request.rider_phone if contacts_visible else None,
            driver_phone=request.driver_phone if contacts_visible else None,
        ))
    return CarpoolDetailResponse(
        trip=trip_response(db, trip, user_id),
        linked_trip=trip_response(db, linked, user_id) if linked else None, requests=requests,
    )


def request_seats(db: Session, trip_id: int, user_id: int, data: SeatRequestInput) -> None:
    trip = get_trip(db, trip_id)
    linked = repo.linked_trip(db, trip) if data.include_return else None
    if data.include_return and linked is None:
        raise HTTPException(422, "This trip has no linked return direction.")
    ids = sorted([trip.id] + ([linked.id] if linked else []))
    trips = [get_trip(db, leg_id, lock=True) for leg_id in ids]
    for leg in trips:
        if leg.driver_id == user_id:
            raise HTTPException(403, "You cannot request seats on your own trip.")
        ensure_open(leg)
        if data.passengers > repo.available_seats(db, leg):
            raise HTTPException(409, "There are not enough available seats on each selected direction.")
        if data.bags > data.passengers * leg.bags_per_person:
            raise HTTPException(422, "Your luggage exceeds the allowance on a selected direction.")
        if repo.seat_requests(db, leg.id, user_id):
            raise HTTPException(409, "You already requested this direction. Check its current status.")
    for leg in trips:
        db.add(CarpoolSeatRequest(
            trip_id=leg.id, rider_id=user_id, passengers=data.passengers,
            bags=data.bags, message=data.message, rider_phone=data.rider_phone,
        ))
        notify(db, leg.driver_id, leg, "carpool.seat_requested", "New seat request. Review it to accept or decline.")
    db.commit()


def change_request(
    db: Session, trip_id: int, request_id: int, user_id: int,
    action: Literal["accept", "decline", "cancel"], reason: str | None = None,
) -> None:
    trip = get_trip(db, trip_id, lock=True)
    request = db.get(CarpoolSeatRequest, request_id)
    if request is None or request.trip_id != trip.id or user_id not in (trip.driver_id, request.rider_id):
        raise HTTPException(404, "Seat request not found.")
    owner = trip.driver_id == user_id
    if action in ("accept", "decline") and not owner:
        raise HTTPException(403, "Only the driver can accept or decline seat requests.")
    targets: dict[str, SeatStatus] = {"accept": "CONFIRMED", "decline": "DECLINED", "cancel": "CANCELLED"}
    target = targets[action]
    if request.status == target:
        return
    if action == "cancel":
        ensure_cancellable(trip)
        if request.status not in ("PENDING", "CONFIRMED"):
            raise HTTPException(409, "Only pending or confirmed requests can be cancelled.")
        request.cancellation_reason = reason
    else:
        ensure_open(trip)
        if request.status != "PENDING":
            raise HTTPException(409, "Only pending requests can be accepted or declined.")
    if action == "accept":
        if request.passengers > repo.available_seats(db, trip):
            raise HTTPException(409, "Not enough seats remain. Refresh the trip.")
        request.driver_phone = require_driver(db, trip.driver_id).phone
    request.status = target
    recipient = request.rider_id if owner else trip.driver_id
    messages = {
        "accept": "Your seat request was approved. This direction is confirmed; contact details are available.",
        "decline": "Your seat request was declined.",
        "cancel": "A seat request or confirmed booking was cancelled. Open the trip for the reason.",
    }
    notify(db, recipient, trip, f"carpool.request_{target.lower()}", messages[action])
    db.commit()


def cancel_trip(db: Session, trip_id: int, user_id: int, reason: str) -> None:
    trip = get_trip(db, trip_id, lock=True)
    if trip.driver_id != user_id:
        raise HTTPException(403, "Only the driver can cancel this trip.")
    if trip.status == "CANCELLED":
        return
    ensure_cancellable(trip)
    trip.status = "CANCELLED"
    trip.cancellation_reason = reason
    for request in repo.seat_requests(db, trip.id):
        if request.status in ("PENDING", "CONFIRMED"):
            request.status = "CANCELLED"
            request.cancellation_reason = reason
            notify(db, request.rider_id, trip, "carpool.trip_cancelled", "The driver cancelled this direction. Open the trip for the reason.")
    db.commit()


def browse(
    db: Session, user_id: int, offset: int, limit: int,
    pickup_location_id: str | None, dropoff_location_id: str | None,
    departure_date: date | None, passengers: int, radius_km: int,
) -> CarpoolPageResponse:
    pickup = resolve_post_location(pickup_location_id) if pickup_location_id else None
    dropoff = resolve_post_location(dropoff_location_id) if dropoff_location_id else None
    query = select(CarpoolTrip).where(
        CarpoolTrip.status == "OPEN", CarpoolTrip.pickup_start > utc_now_naive(),
        CarpoolTrip.driver_id != user_id, CarpoolTrip.seats >= passengers,
    ).order_by(CarpoolTrip.pickup_start, CarpoolTrip.id)
    matches = []
    skipped = 0
    for trip in db.scalars(query.execution_options(yield_per=100)):
        if departure_date and trip.pickup_start.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(trip.timezone)).date() != departure_date:
            continue
        if any(location and distance_km(
            saved["latitude"], saved["longitude"], location.latitude, location.longitude,
        ) > radius_km for location, saved in ((pickup, trip.pickup), (dropoff, trip.dropoff))):
            continue
        if repo.available_seats(db, trip) < passengers:
            continue
        if skipped < offset:
            skipped += 1
            continue
        matches.append(trip_response(db, trip, user_id))
        if len(matches) > limit:
            break
    return CarpoolPageResponse(trips=matches[:limit], has_more=len(matches) > limit)
