from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated


LocationQuery = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=300),
]


class LocationSearchRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    query: LocationQuery
    type: Literal["PICKUP"] = "PICKUP"


class LocationDetailsRequest(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    locale: str = Field(default="en", min_length=2, max_length=10)
    provider: Literal["uber_places"] = "uber_places"
    type: Literal["pickup"] = "pickup"


class LocationAddressComponents(BaseModel):
    model_config = ConfigDict(extra="allow")

    CITY: str
    COUNTRY_CODE: str
    FIRST_LEVEL_SUBDIVISION_CODE: str
    HOUSE_NUMBER: str
    POSTAL_CODE: str
    STREET_NAME: str


class LocationDetailsData(BaseModel):
    model_config = ConfigDict(extra="allow")

    addressComponents: LocationAddressComponents
    addressLine1: str
    addressLine2: str
    categories: list[str]
    chainMetadata: Any | None = None
    fullAddress: str
    id: str
    lat: float = Field(ge=-90, le=90)
    long: float = Field(ge=-180, le=180)
    merchantMetadata: Any | None = None
    provider: str
    title: str
    type: Literal["pickup"]


class LocationDetailsResponse(BaseModel):
    status: Literal["success"]
    data: LocationDetailsData


class LocationSearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    addressLine1: str
    addressLine2: str | None = None
    categories: list[str] = Field(default_factory=list)
    confidence: str | None = None
    id: str | None = None
    provider: str | None = None
    savedPlacesMeta: Any | None = None
    source: str | None = None
    tag: str | None = None
    type: str | None = None


class LocationSearchResponse(BaseModel):
    status: str
    data: list[LocationSearchResult]
