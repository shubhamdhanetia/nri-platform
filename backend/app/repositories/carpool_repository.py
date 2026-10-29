from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.carpool import CarpoolSeatRequest, CarpoolTrip


def trip_by_id(db: Session, trip_id: UUID, *, lock: bool = False) -> CarpoolTrip | None:
    query = select(CarpoolTrip).where(CarpoolTrip.id == trip_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return db.scalar(query)


def linked_trip(db: Session, trip: CarpoolTrip) -> CarpoolTrip | None:
    if trip.outbound_id is not None:
        return db.get(CarpoolTrip, trip.outbound_id)
    return db.scalar(select(CarpoolTrip).where(CarpoolTrip.outbound_id == trip.id))


def seat_requests(db: Session, trip_id: UUID, rider_id: UUID | None = None) -> list[CarpoolSeatRequest]:
    query = select(CarpoolSeatRequest).where(CarpoolSeatRequest.trip_id == trip_id)
    if rider_id is not None:
        query = query.where(CarpoolSeatRequest.rider_id == rider_id)
    return list(db.scalars(query.order_by(CarpoolSeatRequest.created_at, CarpoolSeatRequest.id)))


def available_seats(db: Session, trip: CarpoolTrip) -> int:
    reserved = db.scalar(select(func.coalesce(func.sum(CarpoolSeatRequest.passengers), 0)).where(
        CarpoolSeatRequest.trip_id == trip.id, CarpoolSeatRequest.status == "CONFIRMED",
    ))
    return trip.seats - int(reserved or 0)


def my_trips(db: Session, user_id: UUID, offset: int, limit: int) -> list[CarpoolTrip]:
    involved = select(CarpoolSeatRequest.id).where(
        CarpoolSeatRequest.trip_id == CarpoolTrip.id, CarpoolSeatRequest.rider_id == user_id,
    ).exists()
    return list(db.scalars(select(CarpoolTrip).where(
        or_(CarpoolTrip.driver_id == user_id, involved),
    ).order_by(CarpoolTrip.created_at.desc(), CarpoolTrip.id.desc()).offset(offset).limit(limit)))
