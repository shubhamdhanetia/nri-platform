from datetime import date, datetime, time, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, String, any_, bindparam, case, cast, exists, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session

from app.models.ride import DriverProfile, RideBooking, RideOffer, RideRequest
from app.schemas.post import PostLocationFields, PostSearchBounds
from app.core.ride_time import utc_now_naive
from app.schemas.ride import RideTableSearchInput


def driver_profile(db: Session, user_id: int) -> DriverProfile | None:
    return db.get(DriverProfile, user_id)


def request_by_id(db: Session, request_id: int, *, lock: bool = False) -> RideRequest | None:
    query = select(RideRequest).where(RideRequest.id == request_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return db.scalar(query)


def booking_for_request(db: Session, request_id: int) -> RideBooking | None:
    return db.scalar(select(RideBooking).where(RideBooking.request_id == request_id))


def offers_for_request(db: Session, request_id: int, driver_id: int | None = None) -> list[RideOffer]:
    query = select(RideOffer).where(RideOffer.request_id == request_id)
    if driver_id is not None:
        query = query.where(RideOffer.driver_id == driver_id)
    return list(db.scalars(query.order_by(RideOffer.created_at, RideOffer.id)))


def my_requests(db: Session, user_id: int, offset: int, limit: int) -> list[RideRequest]:
    offered = exists().where(RideOffer.request_id == RideRequest.id, RideOffer.driver_id == user_id)
    query = select(RideRequest).where(or_(RideRequest.rider_id == user_id, offered))
    return list(db.scalars(query.order_by(RideRequest.created_at.desc(), RideRequest.id.desc()).offset(offset).limit(limit)))


def distance_km(lat: float, lng: float, target_lat: float, target_lng: float) -> float:
    a = sin(radians(target_lat - lat) / 2) ** 2 + cos(radians(lat)) * cos(radians(target_lat)) * sin(radians(target_lng - lng) / 2) ** 2
    return 6371 * 2 * asin(sqrt(min(1, max(0, a))))


def open_requests(
    db: Session, user_id: int, offset: int, limit: int,
    pickup: PostLocationFields | None = None, dropoff: PostLocationFields | None = None,
    departure_date: date | None = None, radius_km: int = 25,
    bounds: PostSearchBounds | None = None, cell_ids: set[str] | None = None,
    pickup_time_from: time | None = None, pickup_time_to: time | None = None,
) -> list[RideRequest]:
    query = select(RideRequest).where(
        RideRequest.status == "OPEN",
        RideRequest.pickup_end > utc_now_naive(),
        RideRequest.rider_id != user_id,
    )
    if bounds is not None:
        latitude = RideRequest.pickup["latitude"].as_float()
        longitude = RideRequest.pickup["longitude"].as_float()
        query = query.where(
            RideRequest.pickup["h3_cell_id"].as_string().in_(cell_ids or set()),
            latitude >= bounds.south, latitude <= bounds.north,
        )
        if bounds.east < bounds.west:
            query = query.where(or_(longitude >= bounds.west, longitude <= bounds.east))
        else:
            query = query.where(longitude >= bounds.west, longitude <= bounds.east)
    if departure_date:
        # Broad UTC bounds reduce candidates; final matching uses each trip's timezone.
        start = datetime.combine(departure_date, datetime.min.time())
        query = query.where(RideRequest.pickup_end >= start - timedelta(days=1), RideRequest.pickup_start < start + timedelta(days=2))
    matches: list[RideRequest] = []
    skipped = 0
    for ride in db.scalars(query.order_by(RideRequest.pickup_start, RideRequest.id).execution_options(yield_per=100)):
        if departure_date:
            zone = ZoneInfo(ride.timezone)
            window_start = datetime.combine(departure_date, pickup_time_from or time.min, zone).astimezone(timezone.utc).replace(tzinfo=None)
            window_end = datetime.combine(
                departure_date if pickup_time_to is not None else departure_date + timedelta(days=1),
                (pickup_time_to or time.min).replace(fold=1), zone,
            ).astimezone(timezone.utc).replace(tzinfo=None)
            if ride.pickup_end < window_start:
                continue
            starts_after_range = ride.pickup_start > window_end if pickup_time_to is not None else ride.pickup_start >= window_end
            if starts_after_range:
                continue
        if pickup and distance_km(ride.pickup["latitude"], ride.pickup["longitude"], pickup.latitude, pickup.longitude) > radius_km:
            continue
        if dropoff and distance_km(ride.dropoff["latitude"], ride.dropoff["longitude"], dropoff.latitude, dropoff.longitude) > radius_km:
            continue
        if skipped < offset:
            skipped += 1
            continue
        matches.append(ride)
        if len(matches) == limit:
            break
    return matches


def _local_boundary_utc(local: datetime, *, latest: bool):
    wall = cast(local, DateTime)
    zone = RideRequest.timezone
    before = cast(local - timedelta(days=2), DateTime)
    after = cast(local + timedelta(days=2), DateTime)
    before_offset = before - func.timezone("UTC", func.timezone(zone, before))
    after_offset = after - func.timezone("UTC", func.timezone(zone, after))
    first = wall - before_offset
    second = wall - after_offset
    first_valid = func.timezone(zone, func.timezone("UTC", first)) == wall
    second_valid = func.timezone(zone, func.timezone("UTC", second)) == wall
    # Match ZoneInfo fold=0 at the start and fold=1 at the end of a window.
    return case(
        (first_valid & second_valid, func.greatest(first, second) if latest else func.least(first, second)),
        (first_valid, first), (second_valid, second),
        else_=second if latest else first,
    )


def table_requests(
    db: Session, user_id: int, data: RideTableSearchInput,
    pickup: PostLocationFields | None, cells: set[str] | None,
) -> list[RideRequest]:
    now = utc_now_naive()
    query = select(RideRequest).where(
        RideRequest.status == "OPEN", RideRequest.pickup_end > now,
        RideRequest.pickup_start > now - timedelta(hours=2),
        RideRequest.rider_id != user_id,
    )
    if data.cursor:
        cursor_time = data.cursor.pickup_start.astimezone(timezone.utc).replace(tzinfo=None)
        query = query.where(tuple_(RideRequest.pickup_start, RideRequest.id) > tuple_(cursor_time, data.cursor.id))
    if data.max_passengers is not None:
        query = query.where(RideRequest.passengers <= data.max_passengers)
    if pickup is not None:
        query = query.where(
            RideRequest.pickup["h3_cell_id"].as_string() == any_(bindparam("pickup_cells", sorted(cells or set()), type_=ARRAY(String)))
        )
        latitude = func.radians(RideRequest.pickup["latitude"].as_float())
        longitude = func.radians(RideRequest.pickup["longitude"].as_float())
        cosine = func.sin(latitude) * sin(radians(pickup.latitude)) + func.cos(latitude) * cos(radians(pickup.latitude)) * func.cos(longitude - radians(pickup.longitude))
        query = query.where(6371 * func.acos(func.least(1.0, func.greatest(-1.0, cosine))) <= data.radius_km)
    if data.departure_date:
        start = datetime.combine(data.departure_date, data.pickup_time_from or time.min)
        end = datetime.combine(
            data.departure_date if data.pickup_time_to else data.departure_date + timedelta(days=1),
            data.pickup_time_to or time.min,
        )
        window_start = _local_boundary_utc(start, latest=False)
        window_end = _local_boundary_utc(end, latest=True)
        query = query.where(RideRequest.pickup_end >= window_start)
        query = query.where(RideRequest.pickup_start <= window_end if data.pickup_time_to else RideRequest.pickup_start < window_end)
        query = query.where(RideRequest.pickup_end >= start - timedelta(days=1), RideRequest.pickup_start < end + timedelta(days=1))
    return list(db.scalars(query.order_by(RideRequest.pickup_start, RideRequest.id).limit(data.limit + 1)))
