from datetime import datetime
from decimal import Decimal
from typing import Literal, TypedDict

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.core.ride_time import utc_now_naive

RequestStatus = Literal["OPEN", "CONFIRMED", "CANCELLED", "EXPIRED"]
OfferStatus = Literal["PENDING", "ACCEPTED", "WITHDRAWN", "NOT_SELECTED", "EXPIRED"]
BookingStatus = Literal["CONFIRMED", "COMPLETED", "CANCELLED"]


class RidePlace(TypedDict):
    location_id: str
    location: str
    city: str
    country_code: str
    postal_code: str
    state: str
    latitude: float
    longitude: float
    h3_cell_id: str


class DriverProfile(Base):
    __tablename__ = "driver_profiles"
    __table_args__ = (CheckConstraint("passenger_capacity BETWEEN 1 AND 8"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    vehicle: Mapped[str] = mapped_column(String(100))
    passenger_capacity: Mapped[int]
    phone: Mapped[str] = mapped_column(String(30))
    acknowledgement_at: Mapped[datetime] = mapped_column(DateTime)


class RideRequest(Base):
    __tablename__ = "ride_requests"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','CONFIRMED','CANCELLED','EXPIRED')"),
        CheckConstraint("passengers BETWEEN 1 AND 8"),
        CheckConstraint("bags BETWEEN 0 AND 10"),
        CheckConstraint("pickup_end >= pickup_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rider_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    pickup: Mapped[RidePlace] = mapped_column(JSON)
    dropoff: Mapped[RidePlace] = mapped_column(JSON)
    pickup_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    pickup_end: Mapped[datetime] = mapped_column(DateTime)
    timezone: Mapped[str] = mapped_column(String(100))
    passengers: Mapped[int]
    bags: Mapped[int]
    notes: Mapped[str] = mapped_column(Text)
    rider_phone: Mapped[str] = mapped_column(String(30))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[RequestStatus] = mapped_column(String(12), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


ride_pickup_h3_index = Index("ix_ride_requests_pickup_h3", RideRequest.pickup["h3_cell_id"].as_string())


class RideOffer(Base):
    __tablename__ = "ride_offers"
    __table_args__ = (
        UniqueConstraint("request_id", "driver_id", name="uq_ride_offer_driver"),
        CheckConstraint("status IN ('PENDING','ACCEPTED','WITHDRAWN','NOT_SELECTED','EXPIRED')"),
        CheckConstraint("amount >= 0"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("ride_requests.id"), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    pickup_time: Mapped[datetime] = mapped_column(DateTime)
    amount: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    message: Mapped[str] = mapped_column(Text)
    vehicle: Mapped[str] = mapped_column(String(100))
    passenger_capacity: Mapped[int]
    status: Mapped[OfferStatus] = mapped_column(String(12), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class RideBooking(Base):
    __tablename__ = "ride_bookings"
    __table_args__ = (
        CheckConstraint("status IN ('CONFIRMED','COMPLETED','CANCELLED')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("ride_requests.id"), unique=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("ride_offers.id"), unique=True)
    rider_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    driver_phone: Mapped[str] = mapped_column(String(30))
    rider_phone: Mapped[str] = mapped_column(String(30))
    vehicle: Mapped[str] = mapped_column(String(100))
    pickup_time: Mapped[datetime] = mapped_column(DateTime)
    amount: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[BookingStatus] = mapped_column(String(12), default="CONFIRMED")
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
