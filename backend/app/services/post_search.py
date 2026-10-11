import math

import h3
from fastapi import HTTPException

from app.schemas.post import PostSearchBounds


POST_H3_RESOLUTION = 8
MAX_SEARCH_AREA_SQUARE_KM = 10_000
MAX_SEARCH_CELLS = 20_000
EARTH_RADIUS_KM = 6_371.0088


def _bounds_area_square_km(bounds: PostSearchBounds) -> float:
    longitude_span_degrees = (bounds.east - bounds.west) % 360
    if longitude_span_degrees == 0 and bounds.east > bounds.west:
        longitude_span_degrees = 360
    longitude_span = math.radians(longitude_span_degrees)
    north_sine = math.sin(math.radians(bounds.north))
    south_sine = math.sin(math.radians(bounds.south))
    return EARTH_RADIUS_KM**2 * longitude_span * (north_sine - south_sine)


def h3_cells_for_bounds(bounds: PostSearchBounds) -> set[str]:
    if _bounds_area_square_km(bounds) > MAX_SEARCH_AREA_SQUARE_KM:
        raise HTTPException(
            status_code=422,
            detail="Search area is too large; zoom in and search again",
        )

    longitude_ranges = (
        ((bounds.west, 180), (-180, bounds.east))
        if bounds.east < bounds.west
        else ((bounds.west, bounds.east),)
    )
    cells: set[str] = set()
    for west, east in longitude_ranges:
        polygon = h3.LatLngPoly([
            (bounds.south, west),
            (bounds.south, east),
            (bounds.north, east),
            (bounds.north, west),
        ])
        cells.update(
            h3.polygon_to_cells_experimental(
                polygon,
                POST_H3_RESOLUTION,
                contain="bbox_overlap",
            )
        )
    if len(cells) > MAX_SEARCH_CELLS:
        raise HTTPException(
            status_code=422,
            detail="Search area contains too many map cells; zoom in and search again",
        )
    return set(cells)
