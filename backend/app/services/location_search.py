import h3
import requests

from fastapi import HTTPException
from requests.exceptions import JSONDecodeError, RequestException, Timeout

from app.schemas.post import PostLocationFields
from app.schemas.location import (
    LocationDetailsRequest,
    LocationDetailsResponse,
    LocationSearchRequest,
    LocationSearchResponse,
)


UBER_LOCATION_SEARCH_URL = "https://www.uber.com/api/pudoLocationSearch"
UBER_LOCATION_DETAILS_URL = "https://www.uber.com/api/loadTSPlaceDetails"
UBER_REQUEST_TIMEOUT_SECONDS = 10
UBER_REQUEST_HEADERS = {
    "x-csrf-token": "x",
    "Content-Type": "application/json",
}


def _post_to_uber(url: str, payload: dict[str, object]) -> object:
    try:
        response = requests.post(
            url,
            json=payload,
            headers=UBER_REQUEST_HEADERS,
            timeout=UBER_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except Timeout as error:
        raise HTTPException(
            status_code=504,
            detail="Location provider timed out",
        ) from error
    except RequestException as error:
        raise HTTPException(
            status_code=502,
            detail="Location provider request failed",
        ) from error

    try:
        return response.json()
    except JSONDecodeError as error:
        raise HTTPException(
            status_code=502,
            detail="Location provider returned invalid JSON",
        ) from error


def search_locations(
    request: LocationSearchRequest,
) -> LocationSearchResponse:
    payload = _post_to_uber(
        UBER_LOCATION_SEARCH_URL,
        request.model_dump(),
    )
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "success"
        or not isinstance(payload.get("data"), list)
    ):
        raise HTTPException(
            status_code=502,
            detail="Location provider returned an invalid response",
        )

    try:
        return LocationSearchResponse.model_validate(payload)
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="Location provider returned an invalid response",
        ) from error


def get_location_details(
    request: LocationDetailsRequest,
) -> LocationDetailsResponse:
    payload = _post_to_uber(
        UBER_LOCATION_DETAILS_URL,
        request.model_dump(),
    )
    try:
        return LocationDetailsResponse.model_validate(payload)
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="Location provider returned an invalid response",
        ) from error


def resolve_post_location(location_id: str) -> PostLocationFields:
    details = get_location_details(LocationDetailsRequest(id=location_id)).data
    return PostLocationFields(
        city=details.addressComponents.CITY,
        location_id=details.id,
        location=details.fullAddress,
        country_code=details.addressComponents.COUNTRY_CODE,
        postal_code=details.addressComponents.POSTAL_CODE,
        state=details.addressComponents.FIRST_LEVEL_SUBDIVISION_CODE,
        latitude=details.lat,
        longitude=details.long,
        h3_cell_id=h3.latlng_to_cell(details.lat, details.long, 8),
    )
