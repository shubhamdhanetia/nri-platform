import re
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_serializer, field_validator, model_validator

from app.schemas.post import PostAuthorResponse, PostLocationFields, PostSearchBounds

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=30)]
Currency = Literal["USD", "CAD", "INR", "GBP", "EUR", "AUD"]


class DriverProfileInput(BaseModel):
    vehicle: ShortText
    passenger_capacity: int = Field(ge=1, le=8)
    phone: Phone
    eligibility_acknowledged: Literal[True]

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
            raise ValueError("Use an international phone number, e.g. +14155550123")
        return value


class DriverProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    vehicle: str
    passenger_capacity: int
    phone: str


class RideRequestInput(BaseModel):
    pickup_location_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    dropoff_location_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    pickup_start: AwareDatetime
    pickup_end: AwareDatetime
    timezone: str = Field(max_length=100)
    passengers: int = Field(ge=1, le=8)
    bags: int = Field(ge=0, le=10)
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""
    rider_phone: Phone
    currency: Currency
    exact_location_consent: Literal[True]

    @field_validator("rider_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return DriverProfileInput.validate_phone(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("Select a valid IANA timezone") from error
        return value

    @model_validator(mode="after")
    def validate_window(self) -> "RideRequestInput":
        start = self.pickup_start.astimezone(timezone.utc)
        end = self.pickup_end.astimezone(timezone.utc)
        if start <= datetime.now(timezone.utc):
            raise ValueError("Pickup must be in the future")
        if end < start or (end - start).total_seconds() > 7200:
            raise ValueError("Pickup window must be between zero and two hours")
        if self.pickup_location_id == self.dropoff_location_id:
            raise ValueError("Pickup and drop-off must be different places")
        return self


class RideOfferInput(BaseModel):
    pickup_time: AwareDatetime
    amount: Decimal = Field(ge=0, le=9999.99, max_digits=6, decimal_places=2, allow_inf_nan=False)
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class ConfirmationInput(BaseModel):
    offer_id: int = Field(gt=0)


class CancellationInput(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class UTCResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("pickup_start", "pickup_end", "pickup_time", "created_at", check_fields=False)
    def serialize_datetime(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat()


class RideRequestResponse(UTCResponse):
    id: int
    rider_id: int
    rider: PostAuthorResponse
    pickup: PostLocationFields
    dropoff: PostLocationFields
    pickup_start: datetime
    pickup_end: datetime
    timezone: str
    passengers: int
    bags: int
    notes: str
    currency: Currency
    status: Literal["OPEN", "CONFIRMED", "CANCELLED", "EXPIRED"]
    booking_status: Literal["CONFIRMED", "COMPLETED", "CANCELLED"] | None = None
    my_offer_status: Literal["PENDING", "ACCEPTED", "WITHDRAWN", "NOT_SELECTED", "EXPIRED"] | None = None
    created_at: datetime


class RideOfferResponse(UTCResponse):
    id: int
    request_id: int
    driver_id: int
    driver: PostAuthorResponse
    pickup_time: datetime
    amount: Decimal
    message: str
    vehicle: str
    passenger_capacity: int
    status: Literal["PENDING", "ACCEPTED", "WITHDRAWN", "NOT_SELECTED", "EXPIRED"]
    created_at: datetime


class RideBookingResponse(UTCResponse):
    id: int
    request_id: int
    offer_id: int
    rider_id: int
    driver_id: int
    rider: PostAuthorResponse
    driver: PostAuthorResponse
    driver_phone: str
    rider_phone: str
    vehicle: str
    pickup_time: datetime
    amount: Decimal
    currency: Currency
    status: Literal["CONFIRMED", "COMPLETED", "CANCELLED"]
    cancellation_reason: str | None
    cancelled_by: int | None
    created_at: datetime


class RideDetailResponse(BaseModel):
    request: RideRequestResponse
    offers: list[RideOfferResponse]
    booking: RideBookingResponse | None


class RideMapSearchInput(BaseModel):
    bounds: PostSearchBounds
    limit: int = Field(default=50, ge=1, le=50)
    dropoff_location_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    departure_date: date | None = None
    radius_km: int = Field(default=25, ge=1, le=100)
    pickup_time_from: time | None = None
    pickup_time_to: time | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "RideMapSearchInput":
        if self.pickup_time_from is None and self.pickup_time_to is None:
            return self
        if self.departure_date is None or self.pickup_time_from is None or self.pickup_time_to is None:
            raise ValueError("Select a departure date and both pickup time endpoints")
        if self.pickup_time_from.tzinfo is not None or self.pickup_time_to.tzinfo is not None:
            raise ValueError("Pickup times must be local clock times without a timezone offset")
        if self.pickup_time_to <= self.pickup_time_from:
            raise ValueError("Pickup time range must end after it starts on the same day")
        return self


class RideMapSearchResponse(BaseModel):
    rides: list[RideRequestResponse]
    has_more: bool
