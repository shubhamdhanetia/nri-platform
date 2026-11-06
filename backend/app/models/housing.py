from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ride_time import utc_now_naive
from app.db.base import Base
from app.models.user import User


class HousingPost(Base):
    __tablename__ = "housing_posts"
    __table_args__ = (
        CheckConstraint("kind IN ('LISTING','REQUEST','TOGETHER')", name="housing_kind"),
        CheckConstraint("status IN ('ACTIVE','FILLED','ARCHIVED')", name="housing_status"),
        CheckConstraint("room_type IN ('SHARED','PRIVATE','HALL','ENTIRE','ANY')", name="housing_room_type"),
        CheckConstraint("bedroom_count IS NULL OR bedroom_count BETWEEN 0 AND 20", name="housing_bedroom_count"),
        CheckConstraint("bathroom_count IS NULL OR bathroom_count BETWEEN 0.5 AND 20", name="housing_bathroom_count"),
        CheckConstraint("arrangement IN ('HOUSEHOLD','RENTAL','SUBLET','TAKEOVER','ANY')", name="housing_arrangement"),
        CheckConstraint("kind != 'LISTING' OR (room_type != 'ANY' AND arrangement != 'ANY')", name="housing_listing_space"),
        CheckConstraint("stay_type IN ('SHORT_TERM','LONG_TERM','FLEXIBLE')", name="housing_stay"),
        CheckConstraint("price_period IN ('MONTH','WEEK','NIGHT')", name="housing_period"),
        CheckConstraint("amount >= 0 AND (deposit IS NULL OR deposit >= 0) AND (fees IS NULL OR fees >= 0)", name="housing_amounts"),
        CheckConstraint("available_until IS NULL OR available_until >= available_from", name="housing_dates"),
        CheckConstraint("minimum_stay_days BETWEEN 1 AND 3650 AND available_spaces BETWEEN 1 AND 20 AND (occupants IS NULL OR occupants BETWEEN 0 AND 50)", name="housing_occupancy"),
        CheckConstraint("furnishing IN ('FURNISHED','PARTLY','UNFURNISHED','UNSPECIFIED')", name="housing_furnishing"),
        CheckConstraint("bathroom IN ('PRIVATE','SHARED','UNSPECIFIED')", name="housing_bathroom"),
        CheckConstraint("utilities IN ('INCLUDED','EXTRA','PARTLY','UNKNOWN')", name="housing_utilities"),
        CheckConstraint("approval IN ('NOT_APPLICABLE','REQUIRED','PENDING','OBTAINED')", name="housing_approval"),
        CheckConstraint("arrangement NOT IN ('SUBLET','TAKEOVER') OR approval != 'NOT_APPLICABLE'", name="housing_transfer_approval"),
        CheckConstraint("kitchen IN ('VEGETARIAN','EGGS_ALLOWED','UNRESTRICTED','UNSPECIFIED')", name="housing_kitchen"),
        CheckConstraint("smoking IN ('NO','OUTSIDE','YES','UNSPECIFIED')", name="housing_smoking"),
        CheckConstraint("alcohol IN ('NO','YES','UNSPECIFIED')", name="housing_alcohol"),
        CheckConstraint("pets IN ('NO','ALLOWED','PRESENT','UNSPECIFIED')", name="housing_pets"),
        Index("ix_housing_discovery", "status", "is_private", "expires_at", "created_at", "id"),
        Index("ix_housing_owner_created", "owner_id", "created_at", "id"),
        Index("ix_housing_city", "city"),
        Index("ix_housing_posts_h3_cell_id", "h3_cell_id"),
        CheckConstraint(
            "(location_id IS NULL AND location IS NULL AND latitude IS NULL AND longitude IS NULL "
            "AND h3_cell_id IS NULL AND state IS NULL AND postal_code IS NULL) OR "
            "(location_id IS NOT NULL AND location IS NOT NULL AND latitude IS NOT NULL AND longitude IS NOT NULL "
            "AND h3_cell_id IS NOT NULL AND state IS NOT NULL AND postal_code IS NOT NULL "
            "AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
            name="housing_location_complete",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(10))
    room_type: Mapped[str] = mapped_column(String(10))
    bedroom_count: Mapped[int | None] = mapped_column(nullable=True)
    bathroom_count: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    arrangement: Mapped[str] = mapped_column(String(12))
    stay_type: Mapped[str] = mapped_column(String(12))
    city: Mapped[str] = mapped_column(String(100))
    area: Mapped[str] = mapped_column(String(150))
    country_code: Mapped[str] = mapped_column(String(2))
    location_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    h3_cell_id: Mapped[str | None] = mapped_column(String(15), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    currency: Mapped[str] = mapped_column(String(3))
    price_period: Mapped[str] = mapped_column(String(5))
    available_from: Mapped[date] = mapped_column(Date)
    available_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    minimum_stay_days: Mapped[int]
    furnishing: Mapped[str] = mapped_column(String(12))
    bathroom: Mapped[str] = mapped_column(String(12))
    occupants: Mapped[int | None]
    available_spaces: Mapped[int]
    utilities: Mapped[str] = mapped_column(String(8))
    deposit: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    fees: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    approval: Mapped[str] = mapped_column(String(14))
    kitchen: Mapped[str] = mapped_column(String(14))
    smoking: Mapped[str] = mapped_column(String(12))
    alcohol: Mapped[str] = mapped_column(String(12))
    pets: Mapped[str] = mapped_column(String(12))
    parking: Mapped[bool | None]
    laundry: Mapped[bool | None]
    kitchen_access: Mapped[bool | None]
    work_from_home: Mapped[bool | None]
    household_languages: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    household_notes: Mapped[str] = mapped_column(Text)
    accessibility_notes: Mapped[str] = mapped_column(Text)
    photo_urls: Mapped[list[str]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(8), default="ACTIVE", server_default="ACTIVE")
    is_private: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    owner: Mapped[User] = relationship()


class HousingSave(Base):
    __tablename__ = "housing_saves"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    housing_id: Mapped[UUID] = mapped_column(ForeignKey("housing_posts.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class HousingInquiry(Base):
    __tablename__ = "housing_inquiries"
    __table_args__ = (
        UniqueConstraint("housing_id", "sender_id", name="uq_housing_inquiry_sender"),
        Index("ix_housing_inquiry_sender", "sender_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    housing_id: Mapped[UUID] = mapped_column(ForeignKey("housing_posts.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    housing: Mapped[HousingPost] = relationship()
    sender: Mapped[User] = relationship()
    messages: Mapped[list["HousingMessage"]] = relationship(
        cascade="all, delete-orphan", order_by="HousingMessage.created_at, HousingMessage.id",
    )


class HousingMessage(Base):
    __tablename__ = "housing_messages"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    inquiry_id: Mapped[UUID] = mapped_column(ForeignKey("housing_inquiries.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class HousingReport(Base):
    __tablename__ = "housing_reports"
    __table_args__ = (
        UniqueConstraint("housing_id", "reporter_id", name="uq_housing_report_user"),
        CheckConstraint("reason IN ('SCAM','INACCURATE','DISCRIMINATION','OTHER')", name="housing_report_reason"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    housing_id: Mapped[UUID] = mapped_column(ForeignKey("housing_posts.id", ondelete="CASCADE"), index=True)
    reporter_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(14))
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
