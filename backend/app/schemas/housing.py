from datetime import date, datetime
from decimal import Decimal
from ipaddress import ip_address
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.post import PostSearchBounds

Kind = Literal["LISTING", "REQUEST", "TOGETHER"]
Room = Literal["SHARED", "PRIVATE", "HALL", "ENTIRE", "ANY"]
Arrangement = Literal["HOUSEHOLD", "RENTAL", "SUBLET", "TAKEOVER", "ANY"]
Stay = Literal["SHORT_TERM", "LONG_TERM", "FLEXIBLE"]
Period = Literal["MONTH", "WEEK", "NIGHT"]
Furnishing = Literal["FURNISHED", "PARTLY", "UNFURNISHED", "UNSPECIFIED"]
Bathroom = Literal["PRIVATE", "SHARED", "UNSPECIFIED"]
Kitchen = Literal["VEGETARIAN", "EGGS_ALLOWED", "UNRESTRICTED", "UNSPECIFIED"]
Status = Literal["ACTIVE", "FILLED", "ARCHIVED"]
Money = Annotated[Decimal, Field(ge=0, le=Decimal("999999.99"), max_digits=8, decimal_places=2)]
HouseholdLanguage = Literal["en", "es", "hi", "gu", "te", "ta", "pa", "bn", "mr", "ml", "kn", "ur"]


class HouseholdLanguageFields(BaseModel):
    household_languages: list[HouseholdLanguage] = Field(default_factory=list, max_length=12)

    @field_validator("household_languages")
    @classmethod
    def unique_household_languages(cls, values: list[HouseholdLanguage]) -> list[HouseholdLanguage]:
        return list(dict.fromkeys(values))


class HousingContent(HouseholdLanguageFields):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=5, max_length=150)
    description: str = Field(min_length=10, max_length=5000)
    kind: Kind
    room_type: Room
    bedroom_count: int | None = Field(default=None, ge=0, le=20)
    bathroom_count: Decimal | None = Field(default=None, ge=Decimal("0.5"), le=Decimal("20"), max_digits=3, decimal_places=1, multiple_of=Decimal("0.5"))
    arrangement: Arrangement
    stay_type: Stay
    area: str = Field(default="", max_length=150)
    amount: Money
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_period: Period
    available_from: date
    available_until: date | None = None
    minimum_stay_days: int = Field(default=30, ge=1, le=3650)
    furnishing: Furnishing = "UNSPECIFIED"
    bathroom: Bathroom = "UNSPECIFIED"
    occupants: int | None = Field(default=None, ge=0, le=50)
    available_spaces: int = Field(default=1, ge=1, le=20)
    utilities: Literal["INCLUDED", "EXTRA", "PARTLY", "UNKNOWN"] = "UNKNOWN"
    deposit: Money | None = None
    fees: Money | None = None
    approval: Literal["NOT_APPLICABLE", "REQUIRED", "PENDING", "OBTAINED"] = "NOT_APPLICABLE"
    kitchen: Kitchen = "UNSPECIFIED"
    smoking: Literal["NO", "OUTSIDE", "YES", "UNSPECIFIED"] = "UNSPECIFIED"
    alcohol: Literal["NO", "YES", "UNSPECIFIED"] = "UNSPECIFIED"
    pets: Literal["NO", "ALLOWED", "PRESENT", "UNSPECIFIED"] = "UNSPECIFIED"
    parking: bool | None = None
    laundry: bool | None = None
    kitchen_access: bool | None = None
    work_from_home: bool | None = None
    household_notes: str = Field(default="", max_length=2000)
    accessibility_notes: str = Field(default="", max_length=1000)
    photo_urls: list[str] = Field(default_factory=list, max_length=8)
    is_private: bool = False

    @field_validator("photo_urls")
    @classmethod
    def public_https_photos(cls, values: list[str]) -> list[str]:
        result = []
        for value in values:
            value = value.strip()
            parts = urlsplit(value)
            host = parts.hostname or ""
            if (len(value) > 2000 or parts.scheme != "https" or not host
                    or parts.username is not None or parts.password is not None
                    or any(char.isspace() or ord(char) < 32 for char in value)
                    or "\\" in value or parts.port not in (None, 443)):
                raise ValueError("Photo links must be public HTTPS image URLs without credentials.")
            if "." not in host or host.endswith((".localhost", ".local", ".internal")):
                raise ValueError("Local-network photo links are not allowed.")
            try:
                address = ip_address(host)
            except ValueError:
                address = None
            if address is not None and not address.is_global:
                raise ValueError("Local-network photo links are not allowed.")
            result.append(value)
        return result

    @model_validator(mode="after")
    def validate_arrangement(self) -> Self:
        if self.available_until and self.available_until < self.available_from:
            raise ValueError("End date must be on or after the start date.")
        if self.available_until and (self.available_until - self.available_from).days + 1 < self.minimum_stay_days:
            raise ValueError("The available date range must cover the minimum stay.")
        if self.kind == "LISTING" and (self.room_type == "ANY" or self.arrangement == "ANY"):
            raise ValueError("Available places need a specific space and arrangement.")
        if self.arrangement in ("SUBLET", "TAKEOVER") and self.approval == "NOT_APPLICABLE":
            raise ValueError("State whether landlord approval is required, pending, or obtained.")
        return self


class HousingInput(HousingContent):
    location_id: str = Field(min_length=1, max_length=200)


class HousingMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    picture: str | None


class HousingResponse(HousingContent):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owner_id: UUID
    status: Status
    created_at: datetime
    updated_at: datetime | None
    expires_at: datetime
    my_saved: bool = False
    owner: HousingMember
    city: str
    country_code: str
    location_id: str | None
    location: str | None
    latitude: float | None
    longitude: float | None
    h3_cell_id: str | None
    state: str | None
    postal_code: str | None


class HousingCollection(BaseModel):
    items: list[HousingResponse]
    has_more: bool


class HousingSearch(HouseholdLanguageFields):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    view: Literal["PLACES", "PEOPLE", "ROOMMATES"] = "PLACES"
    query: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    bounds: PostSearchBounds | None = None
    kind: Kind | None = None
    room_type: Room | None = None
    min_bedrooms: int | None = Field(default=None, ge=0, le=20)
    min_bathrooms: Decimal | None = Field(default=None, ge=Decimal("0.5"), le=Decimal("20"), max_digits=3, decimal_places=1, multiple_of=Decimal("0.5"))
    arrangement: Arrangement | None = None
    stay_type: Stay | None = None
    min_amount: Money | None = None
    max_amount: Money | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    price_period: Period | None = None
    available_from: date | None = None
    available_until: date | None = None
    furnishing: Furnishing | None = None
    bathroom: Bathroom | None = None
    kitchen: Kitchen | None = None
    parking: bool | None = None
    laundry: bool | None = None
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=10000)

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        if self.view == "PLACES" and self.kind not in (None, "LISTING"):
            raise ValueError("Find a place only shows available listings. Use Find people for housing requests and searching together.")
        if self.view != "PLACES" and self.kind == "LISTING":
            raise ValueError("Find people only shows housing requests and searching-together posts. Use Find a place for available listings.")
        if (self.min_amount is not None or self.max_amount is not None) and (not self.currency or not self.price_period):
            raise ValueError("Budget filtering requires a currency and price period.")
        if self.min_amount is not None and self.max_amount is not None and self.min_amount > self.max_amount:
            raise ValueError("Minimum budget cannot exceed maximum budget.")
        if self.available_from and self.available_until and self.available_until < self.available_from:
            raise ValueError("End date cannot precede move-in date.")
        return self


class HousingStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Status


class HousingVisibilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_private: bool


class HousingMessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=2000)


class HousingMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sender_id: UUID
    content: str
    created_at: datetime


class HousingInquiryResponse(BaseModel):
    id: UUID
    housing_id: UUID
    housing_title: str
    sender: HousingMember
    owner: HousingMember
    created_at: datetime
    messages: list[HousingMessageResponse]


class HousingInquiryCollection(BaseModel):
    items: list[HousingInquiryResponse]
    has_more: bool


class HousingReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: Literal["SCAM", "INACCURATE", "DISCRIMINATION", "OTHER"]
    details: str = Field(min_length=5, max_length=2000)


class HousingReportResponse(BaseModel):
    id: UUID
    detail: str
