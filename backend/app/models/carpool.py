from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ride_time import utc_now_naive
from app.db.base import Base
from app.models.ride import RidePlace

SeatStatus = Literal["PENDING", "CONFIRMED", "DECLINED", "CANCELLED"]


class CarpoolTrip(Base):
    __tablename__ = "carpool_trips"
    __table_args__ = (
        CheckConstraint("seats BETWEEN 1 AND 8"),
        CheckConstraint("bags_per_person BETWEEN 0 AND 10"),
        CheckConstraint("amount >= 0"),
        CheckConstraint("pickup_end >= pickup_start"),
        CheckConstraint("status IN ('OPEN','CANCELLED')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    outbound_id: Mapped[int | None] = mapped_column(ForeignKey("carpool_trips.id"), unique=True)
    pickup: Mapped[RidePlace] = mapped_column(JSON)
    dropoff: Mapped[RidePlace] = mapped_column(JSON)
    pickup_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    pickup_end: Mapped[datetime] = mapped_column(DateTime)
    timezone: Mapped[str] = mapped_column(String(100))
    seats: Mapped[int]
    bags_per_person: Mapped[int]
    amount: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    currency: Mapped[str] = mapped_column(String(3))
    vehicle: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str] = mapped_column(Text)
    status: Mapped[Literal["OPEN", "CANCELLED"]] = mapped_column(String(12), default="OPEN", index=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


carpool_pickup_h3_index = Index("ix_carpool_trips_pickup_h3", CarpoolTrip.pickup["h3_cell_id"].as_string())
carpool_dropoff_h3_index = Index("ix_carpool_trips_dropoff_h3", CarpoolTrip.dropoff["h3_cell_id"].as_string())


class CarpoolSeatRequest(Base):
    __tablename__ = "carpool_seat_requests"
    __table_args__ = (
        UniqueConstraint("trip_id", "rider_id", name="uq_carpool_trip_rider"),
        CheckConstraint("passengers BETWEEN 1 AND 8"),
        CheckConstraint("bags BETWEEN 0 AND 80"),
        CheckConstraint("status IN ('PENDING','CONFIRMED','DECLINED','CANCELLED')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("carpool_trips.id"), index=True)
    rider_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    passengers: Mapped[int]
    bags: Mapped[int]
    message: Mapped[str] = mapped_column(Text)
    rider_phone: Mapped[str] = mapped_column(String(30))
    driver_phone: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[SeatStatus] = mapped_column(String(12), default="PENDING")
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
