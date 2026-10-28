from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, field_validator, model_validator

from app.schemas.post import PostAuthorResponse, PostLocationFields, PostSearchBounds
from app.schemas.common import UTCResponse
from app.schemas.ride import Currency, DriverProfileInput, Phone, RideRequestInput, validate_pickup_window

Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
LocationID = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
SeatResponseStatus = Literal["PENDING", "CONFIRMED", "DECLINED", "CANCELLED", "EXPIRED"]
TripResponseStatus = Literal["OPEN", "FULL", "DEPARTED", "CANCELLED"]


class CarpoolLegInput(BaseModel):
    pickup_location_id: LocationID
    dropoff_location_id: LocationID
    pickup_start: AwareDatetime
    pickup_end: AwareDatetime
    timezone: str = Field(max_length=100)
    seats: int = Field(ge=1, le=8)
    bags_per_person: int = Field(ge=0, le=10)
    amount: Decimal = Field(ge=0, le=9999.99, max_digits=6, decimal_places=2, allow_inf_nan=False)
    currency: Currency
    notes: Notes = ""

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return RideRequestInput.validate_timezone(value)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        validate_pickup_window(self.pickup_start, self.pickup_end, self.pickup_location_id, self.dropoff_location_id)
        return self


class CarpoolCreateInput(BaseModel):
    outbound: CarpoolLegInput
    return_trip: CarpoolLegInput | None = None
    public_meeting_point_consent: Literal[True]

    @model_validator(mode="after")
    def validate_return(self) -> Self:
        if self.return_trip and self.return_trip.pickup_start <= self.outbound.pickup_end:
            raise ValueError("The return trip must start after the outbound departure window")
        return self


class SeatRequestInput(BaseModel):
    passengers: int = Field(ge=1, le=8)
    bags: int = Field(ge=0, le=80)
    message: Notes = ""
    rider_phone: Phone
    include_return: bool = False

    @field_validator("rider_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return DriverProfileInput.validate_phone(value)


class CarpoolTripResponse(UTCResponse):
    id: int
    driver_id: int
    driver: PostAuthorResponse
    linked_trip_id: int | None
    is_return: bool
    pickup: PostLocationFields
    dropoff: PostLocationFields
    pickup_start: datetime
    pickup_end: datetime
    timezone: str
    seats: int
    available_seats: int
    bags_per_person: int
    amount: Decimal
    currency: Currency
    vehicle: str
    notes: str
    status: TripResponseStatus
    can_cancel: bool
    cancellation_reason: str | None
    my_request_status: SeatResponseStatus | None
    created_at: datetime


class SeatRequestResponse(UTCResponse):
    id: int
    trip_id: int
    rider: PostAuthorResponse
    passengers: int
    bags: int
    message: str
    status: SeatResponseStatus
    rider_phone: str | None
    driver_phone: str | None
    cancellation_reason: str | None
    created_at: datetime


class CarpoolDetailResponse(BaseModel):
    trip: CarpoolTripResponse
    linked_trip: CarpoolTripResponse | None
    requests: list[SeatRequestResponse]


class CarpoolPageResponse(BaseModel):
    trips: list[CarpoolTripResponse]
    has_more: bool


class CarpoolMapSearchInput(BaseModel):
    bounds: PostSearchBounds
    scope: Literal["pickup", "destination"] = "pickup"
    pickup_location_id: LocationID | None = None
    dropoff_location_id: LocationID | None = None
    departure_date: date | None = None
    passengers: int = Field(default=1, ge=1, le=8)
    radius_km: float = Field(default=25, ge=1, le=100, allow_inf_nan=False)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=50)
