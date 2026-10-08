from fastapi import APIRouter

from app.schemas.location import (
    LocationDetailsRequest,
    LocationDetailsResponse,
    LocationSearchRequest,
    LocationSearchResponse,
)
from app.services.location_search import get_location_details, search_locations


router = APIRouter()


@router.post(
    "/search",
    response_model=LocationSearchResponse,
    response_model_exclude_unset=True,
)
def search(
    request: LocationSearchRequest,
) -> LocationSearchResponse:
    return search_locations(request)


@router.post(
    "/details",
    response_model=LocationDetailsResponse,
)
def details(
    request: LocationDetailsRequest,
) -> LocationDetailsResponse:
    return get_location_details(request)
