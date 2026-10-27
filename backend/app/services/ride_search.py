import math

import h3
from fastapi import HTTPException

from app.schemas.post import PostLocationFields
from app.services.post_search import POST_H3_RESOLUTION


def pickup_radius_cells(pickup: PostLocationFields, radius_km: float) -> set[str]:
    angular_radius = radius_km / 6371
    latitude = math.radians(pickup.latitude)
    south = max(-90, pickup.latitude - math.degrees(angular_radius))
    north = min(90, pickup.latitude + math.degrees(angular_radius))
    if south == -90 or north == 90:
        west, east = -180.0, 180.0
    else:
        span = math.degrees(math.asin(min(1, math.sin(angular_radius) / math.cos(latitude))))
        west, east = pickup.longitude - span, pickup.longitude + span
    cells: set[str] = set()
    # Small longitude slices also cover polar caps and antimeridian crossings.
    while west < east:
        edge = min(east, west + 90, (math.floor((west + 180) / 360) + 1) * 360 - 180)
        if edge <= west:
            edge = min(east, west + 90)
        shift = 360 * math.floor((west + 180) / 360)
        polygon = h3.LatLngPoly([(south, west - shift), (south, edge - shift),
                                (north, edge - shift), (north, west - shift)])
        cells.update(h3.polygon_to_cells_experimental(polygon, POST_H3_RESOLUTION, contain="bbox_overlap"))
        if len(cells) > 200_000:
            raise HTTPException(422, "Pickup area contains too many cells; use a smaller radius")
        west = edge
    return cells
