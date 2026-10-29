from uuid import UUID

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ride import DriverProfile, RideBooking, RideOffer, RideRequest
from app.models.user import User
from app.core.ride_time import utc_now_naive
from app.repositories import ride_repository as repo
from app.schemas.post import PostAuthorResponse
from app.schemas.ride import (
    DriverProfileInput, RideBookingResponse, RideDetailResponse, RideOfferInput,
    RideOfferResponse, RideRequestInput, RideRequestResponse,
)
from app.services.location_search import resolve_post_location
from app.services import notifications


def utc_naive(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def require_driver(db: Session, user_id: UUID) -> DriverProfile:
    profile = repo.driver_profile(db, user_id)
    if profile is None:
        raise HTTPException(403, "Complete your driver profile before offering rides.")
    return profile


def save_driver(db: Session, user_id: UUID, data: DriverProfileInput) -> DriverProfile:
    # Lock the existing parent so two initial profile saves cannot race to insert.
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    profile = repo.driver_profile(db, user_id)
    if profile is None:
        profile = DriverProfile(user_id=user_id)
        db.add(profile)
    profile.vehicle = data.vehicle
    profile.passenger_capacity = data.passenger_capacity
    profile.phone = data.phone
    profile.acknowledgement_at = utc_now_naive()
    db.commit()
    db.refresh(profile)
    return profile


def create_request(db: Session, user_id: UUID, data: RideRequestInput) -> RideRequest:
    pickup = resolve_post_location(data.pickup_location_id)
    dropoff = resolve_post_location(data.dropoff_location_id)
    if pickup.location_id == dropoff.location_id or (
        pickup.latitude == dropoff.latitude and pickup.longitude == dropoff.longitude
    ):
        raise HTTPException(422, "Pickup and drop-off must be different places.")
    if utc_naive(data.pickup_start) <= utc_now_naive():
        raise HTTPException(422, "Pickup must be in the future.")
    ride = RideRequest(
        rider_id=user_id, pickup=pickup.model_dump(), dropoff=dropoff.model_dump(),
        pickup_start=utc_naive(data.pickup_start), pickup_end=utc_naive(data.pickup_end),
        timezone=data.timezone, passengers=data.passengers, bags=data.bags,
        notes=data.notes, rider_phone=data.rider_phone, currency=data.currency,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride


def get_request(db: Session, request_id: UUID, user_id: UUID, *, lock: bool = False) -> RideRequest:
    ride = repo.request_by_id(db, request_id, lock=lock)
    if ride is None:
        raise HTTPException(404, "Ride request not found.")
    if ride.rider_id != user_id:
        booking = repo.booking_for_request(db, ride.id)
        if booking is None or booking.driver_id != user_id:
            has_offer = bool(repo.offers_for_request(db, ride.id, user_id))
            if (ride.status != "OPEN" or ride.pickup_end <= utc_now_naive()) and not has_offer:
                raise HTTPException(404, "Ride request not found.")
    return ride


def ensure_open(ride: RideRequest) -> None:
    if ride.status != "OPEN" or ride.pickup_end <= utc_now_naive():
        raise HTTPException(409, "This request is no longer open. Refresh to see its current status.")


def notify_member(db: Session, user_id: UUID, ride: RideRequest, event_type: str, message: str) -> None:
    route = f"{ride.pickup['city']} to {ride.dropoff['city']}"
    notifications.notify(
        db, user_id=user_id, category="ride", event_type=event_type,
        resource_id=ride.id, target_path=f"/rides/{ride.id}", message=f"{message} ({route})"[:500],
    )


def send_offer(db: Session, request_id: UUID, user_id: UUID, data: RideOfferInput) -> RideOffer:
    profile = require_driver(db, user_id)
    ride = get_request(db, request_id, user_id, lock=True)
    if ride.rider_id == user_id:
        raise HTTPException(403, "You cannot offer a ride on your own request.")
    ensure_open(ride)
    pickup_time = utc_naive(data.pickup_time)
    if not ride.pickup_start <= pickup_time <= ride.pickup_end or pickup_time <= utc_now_naive():
        raise HTTPException(422, "Choose a future pickup time within the requested window.")
    if profile.passenger_capacity < ride.passengers:
        raise HTTPException(422, "Your vehicle does not have enough passenger seats.")
    existing = repo.offers_for_request(db, ride.id, user_id)
    can_resubmit = bool(existing) and (
        existing[0].status in ("WITHDRAWN", "EXPIRED")
        or (existing[0].status == "PENDING" and existing[0].pickup_time <= utc_now_naive())
    )
    if existing and not can_resubmit:
        raise HTTPException(409, "You already have an offer on this request.")
    offer = existing[0] if existing else RideOffer(request_id=ride.id, driver_id=user_id)
    offer.pickup_time = pickup_time
    offer.amount = data.amount
    offer.message = data.message
    offer.vehicle = profile.vehicle
    offer.passenger_capacity = profile.passenger_capacity
    offer.status = "PENDING"
    offer.created_at = utc_now_naive()
    db.add(offer)
    notify_member(db, ride.rider_id, ride, "ride.offer_received", "A driver offered to help with your ride. Review the offer.")
    db.commit()
    db.refresh(offer)
    return offer


def withdraw_offer(db: Session, request_id: UUID, offer_id: UUID, user_id: UUID) -> None:
    ride = get_request(db, request_id, user_id, lock=True)
    offer = db.get(RideOffer, offer_id)
    if offer is None or offer.request_id != ride.id or offer.driver_id != user_id:
        raise HTTPException(404, "Offer not found.")
    if offer.status == "WITHDRAWN":
        return
    ensure_open(ride)
    if offer.status != "PENDING":
        raise HTTPException(409, "Only a pending offer can be withdrawn.")
    offer.status = "WITHDRAWN"
    notify_member(db, ride.rider_id, ride, "ride.offer_withdrawn", "A driver withdrew their offer.")
    db.commit()


def confirm(db: Session, request_id: UUID, offer_id: UUID, user_id: UUID) -> RideBooking:
    ride = get_request(db, request_id, user_id, lock=True)
    if ride.rider_id != user_id:
        raise HTTPException(403, "Only the rider can choose a driver.")
    booking = repo.booking_for_request(db, request_id)
    if booking is not None:
        if booking.offer_id == offer_id and booking.status == "CONFIRMED":
            return booking
        raise HTTPException(409, "This request already has a booking.")
    ensure_open(ride)
    offer = db.get(RideOffer, offer_id)
    if offer is None or offer.request_id != ride.id or offer.status != "PENDING":
        raise HTTPException(409, "This offer is no longer available.")
    profile = require_driver(db, offer.driver_id)
    if offer.pickup_time <= utc_now_naive() or profile.passenger_capacity < ride.passengers:
        raise HTTPException(409, "This driver offer is no longer eligible. Choose another offer.")
    booking = RideBooking(
        request_id=ride.id, offer_id=offer.id, rider_id=user_id, driver_id=offer.driver_id,
        driver_phone=profile.phone, rider_phone=ride.rider_phone, vehicle=offer.vehicle,
        pickup_time=offer.pickup_time, amount=offer.amount, currency=ride.currency,
    )
    db.add(booking)
    ride.status = "CONFIRMED"
    for candidate in repo.offers_for_request(db, ride.id):
        if candidate.status == "PENDING":
            candidate.status = "ACCEPTED" if candidate.id == offer.id else "NOT_SELECTED"
            if candidate.id != offer.id:
                notify_member(db, candidate.driver_id, ride, "ride.offer_not_selected", "The rider selected another driver. Your offer is now closed.")
    notify_member(db, offer.driver_id, ride, "ride.booking_confirmed", "The rider accepted your offer. Your ride is confirmed; contact details are available.")
    db.commit()
    db.refresh(booking)
    return booking


def cancel_request(db: Session, request_id: UUID, user_id: UUID) -> None:
    ride = get_request(db, request_id, user_id, lock=True)
    if ride.rider_id != user_id:
        raise HTTPException(403, "Only the rider can cancel the request.")
    if ride.status == "CANCELLED":
        return
    ensure_open(ride)
    ride.status = "CANCELLED"
    for offer in repo.offers_for_request(db, ride.id):
        if offer.status == "PENDING":
            offer.status = "NOT_SELECTED"
            notify_member(db, offer.driver_id, ride, "ride.request_cancelled", "The rider cancelled this ride request.")
    db.commit()


def change_booking(db: Session, request_id: UUID, user_id: UUID, *, reason: str | None = None) -> None:
    ride = get_request(db, request_id, user_id, lock=True)
    booking = repo.booking_for_request(db, request_id)
    if booking is None or user_id not in (booking.rider_id, booking.driver_id):
        raise HTTPException(404, "Booking not found.")
    if reason is None and user_id != booking.rider_id:
        raise HTTPException(403, "Only the rider can mark the ride completed.")
    target = "CANCELLED" if reason is not None else "COMPLETED"
    if booking.status == target:
        return
    if booking.status != "CONFIRMED":
        raise HTTPException(409, "This booking is already closed.")
    if reason is None:
        if ride.pickup_end > utc_now_naive():
            raise HTTPException(409, "A ride cannot be completed before the pickup window ends.")
    else:
        booking.cancelled_by = user_id
        booking.cancellation_reason = reason
        ride.status = "CANCELLED"
    booking.status = target
    recipient = booking.driver_id if user_id == booking.rider_id else booking.rider_id
    notify_member(
        db, recipient, ride,
        "ride.booking_cancelled" if reason is not None else "ride.booking_completed",
        "Your confirmed ride was cancelled. Open the ride for the reason." if reason is not None
        else "The rider marked your ride completed.",
    )
    db.commit()


def author(db: Session, user_id: UUID) -> PostAuthorResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Ride member not found.")
    return PostAuthorResponse.model_validate(user)


def request_response(db: Session, ride: RideRequest, viewer_id: UUID | None = None) -> RideRequestResponse:
    result = RideRequestResponse.model_validate({
        **{column.name: getattr(ride, column.name) for column in RideRequest.__table__.columns},
        "rider": author(db, ride.rider_id),
    })
    if ride.status == "OPEN" and ride.pickup_end <= utc_now_naive():
        result.status = "EXPIRED"
    booking = repo.booking_for_request(db, ride.id)
    if booking is not None:
        result.booking_status = booking.status
    if viewer_id is not None and viewer_id != ride.rider_id:
        offers = repo.offers_for_request(db, ride.id, viewer_id)
        if offers:
            result.my_offer_status = offer_response(db, offers[0], ride).status
    return result


def offer_response(db: Session, offer: RideOffer, ride: RideRequest) -> RideOfferResponse:
    result = RideOfferResponse.model_validate({
        **{column.name: getattr(offer, column.name) for column in RideOffer.__table__.columns},
        "driver": author(db, offer.driver_id),
    })
    if offer.status == "PENDING" and (ride.pickup_end <= utc_now_naive() or offer.pickup_time <= utc_now_naive()):
        result.status = "EXPIRED"
    return result


def booking_response(db: Session, booking: RideBooking) -> RideBookingResponse:
    return RideBookingResponse.model_validate({
        **{column.name: getattr(booking, column.name) for column in RideBooking.__table__.columns},
        "rider": author(db, booking.rider_id), "driver": author(db, booking.driver_id),
    })


def detail(db: Session, ride: RideRequest, user_id: UUID) -> RideDetailResponse:
    booking = repo.booking_for_request(db, ride.id)
    offers = repo.offers_for_request(db, ride.id, None if ride.rider_id == user_id else user_id)
    participant = booking is not None and user_id in (booking.rider_id, booking.driver_id)
    return RideDetailResponse(
        request=request_response(db, ride, user_id),
        offers=[offer_response(db, offer, ride) for offer in offers],
        booking=booking_response(db, booking) if participant and booking is not None else None,
    )
