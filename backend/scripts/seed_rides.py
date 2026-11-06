"""Insert fictional carpools and ride requests into local PostgreSQL only."""

import argparse
import os
from datetime import datetime, time, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.main import app as _app  # Registers related ORM models.
from app.core.config import settings
from app.core.ride_time import utc_now_naive
from app.db.url import parse_database_url
from app.models.carpool import CarpoolTrip
from app.models.ride import DriverProfile, RideRequest
from app.models.user import User
from app.schemas.carpool import CarpoolCreateInput
from app.schemas.location import LocationSearchRequest
from app.schemas.post import PostLocationFields
from app.schemas.ride import DriverProfileInput, RideRequestInput
from app.services.location_search import resolve_post_location, search_locations
from app.services.rides import utc_naive


LOCATIONS = (
    ("Fremont", "Fremont BART Station, Fremont California", 37.557, -121.976),
    ("San Jose", "San Jose Diridon Station California", 37.330, -121.902),
    ("San Francisco", "San Francisco Ferry Building California", 37.795, -122.393),
    ("Oakland", "Oakland Jack London Square California", 37.795, -122.277),
    ("Los Angeles", "Los Angeles Union Station California", 34.056, -118.236),
    ("Pasadena", "Pasadena City Hall California", 34.148, -118.144),
    ("Santa Monica", "Santa Monica Pier California", 34.010, -118.496),
    ("Long Beach", "Long Beach Convention Center California", 33.766, -118.189),
)
# The second leg is a linked same-day return; all others are one-way.
CARPOOLS = (
    ("Fremont", "San Jose", 3, 8, 2, 1, 12, None),
    ("San Jose", "Fremont", 3, 18, 2, 1, 12, 0),
    ("Oakland", "San Francisco", 5, 9, 3, 0, 0, None),
    ("Los Angeles", "Pasadena", 7, 10, 1, 2, 15, None),
    ("Santa Monica", "Los Angeles", 9, 16, 2, 1, 20, None),
    ("Long Beach", "Los Angeles", 12, 11, 4, 2, 25, None),
)
REQUESTS = (
    ("San Jose", "San Francisco", 4, 7, 1, 0, 35),
    ("Fremont", "Oakland", 6, 12, 2, 2, None),
    ("San Francisco", "San Jose", 8, 17, 3, 3, 60),
    ("Pasadena", "Los Angeles", 5, 9, 1, 1, 20),
    ("Los Angeles", "Santa Monica", 10, 14, 2, 0, 0),
    ("Long Beach", "Pasadena", 14, 10, 4, 4, 75),
)
TIMEZONE = "America/Los_Angeles"
LABEL = "[Demo] FICTIONAL SAMPLE ONLY - not a real ride"


def sample_id(owner_id: UUID, kind: str, index: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"nri-platform:rides-demo:v1:{owner_id}:{kind}:{index}")


def validate_local_database(url: URL) -> None:
    if (url.get_backend_name() != "postgresql"
            or url.host not in ("localhost", "127.0.0.1", "::1")
            or {"host", "hostaddr", "service", "servicefile"} & set(url.query)
            or any(os.environ.get(key) for key in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE"))):
        raise RuntimeError("Refusing to seed: this command only supports local PostgreSQL without host/service overrides.")


def validate_migrations(db: Session) -> None:
    scripts = ScriptDirectory(str(Path(__file__).resolve().parents[1] / "migrations"))
    heads = set(scripts.get_heads())
    current = set(db.scalars(text("SELECT version_num FROM alembic_version")))
    if not heads or current != heads:
        raise RuntimeError("Apply migrations to the current Alembic head before seeding.")


def require_existing_profile(db: Session, owner: User) -> DriverProfile:
    profile = db.get(DriverProfile, owner.id)
    if profile is None or profile.acknowledgement_at is None:
        raise RuntimeError(
            "Seeding blocked: complete the existing user's driver profile locally with their real "
            "phone, vehicle, passenger capacity and eligibility acknowledgement. Nothing was inserted."
        )
    DriverProfileInput.model_validate({
        "vehicle": profile.vehicle, "vehicle_color": profile.vehicle_color,
        "passenger_capacity": profile.passenger_capacity, "phone": profile.phone,
        "license_plate": profile.license_plate, "eligibility_acknowledged": True,
    })
    return profile


def pickup_window(now: datetime, days: int, hour: int, minutes: int) -> tuple[datetime, datetime]:
    local_date = now.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(TIMEZONE)).date()
    start = datetime.combine(local_date + timedelta(days=days), time(hour), ZoneInfo(TIMEZONE))
    return start, start + timedelta(minutes=minutes)


def resolve_locations(needed: set[str]) -> dict[str, PostLocationFields]:
    locations = {}
    for area, query, latitude, longitude in LOCATIONS:
        if area not in needed:
            continue
        suggestions = search_locations(LocationSearchRequest(query=query, latitude=latitude, longitude=longitude))
        suggestion = next((item for item in suggestions.data if item.id), None)
        if suggestion is None or suggestion.id is None:
            raise RuntimeError(f"No provider location found for {area}; nothing has been committed.")
        location = resolve_post_location(suggestion.id)
        if (location.country_code != "US" or abs(location.latitude - latitude) > 0.02
                or abs(location.longitude - longitude) > 0.02):
            raise RuntimeError(f"Unexpected provider landmark for {area}; nothing has been committed.")
        locations[area] = location
    return locations


def route_fields(locations: dict[str, PostLocationFields], pickup: str, dropoff: str) -> dict:
    origin, destination = locations[pickup], locations[dropoff]
    if origin.location_id == destination.location_id or (
        origin.latitude == destination.latitude and origin.longitude == destination.longitude
    ):
        raise RuntimeError("Pickup and drop-off must be different public landmarks.")
    return {"pickup": origin.model_dump(), "dropoff": destination.model_dump()}


def build_trip(index: int, owner: User, profile: DriverProfile,
               locations: dict[str, PostLocationFields], now: datetime) -> CarpoolTrip:
    pickup, dropoff, days, hour, seats, bags, amount, outbound = CARPOOLS[index]
    start, end = pickup_window(now, days, hour, 30)
    data = CarpoolCreateInput.model_validate({
        "outbound": {
            "pickup_location_id": locations[pickup].location_id,
            "dropoff_location_id": locations[dropoff].location_id,
            "pickup_start": start, "pickup_end": end, "timezone": TIMEZONE,
            "seats": min(seats, profile.passenger_capacity), "bags_per_person": bags,
            "amount": amount, "currency": "USD",
            "notes": f"{LABEL}. {pickup} to {dropoff}. Public landmark meeting points only. "
                     "Do not travel or pay based on this sample.",
        },
        "public_meeting_point_consent": True,
    }).outbound
    return CarpoolTrip(
        id=sample_id(owner.id, "carpool", index), driver_id=owner.id,
        outbound_id=sample_id(owner.id, "carpool", outbound) if outbound is not None else None,
        **route_fields(locations, pickup, dropoff),
        pickup_start=utc_naive(data.pickup_start), pickup_end=utc_naive(data.pickup_end),
        timezone=data.timezone, seats=data.seats, bags_per_person=data.bags_per_person,
        amount=data.amount, currency=data.currency, notes=data.notes,
        vehicle=profile.vehicle, vehicle_color=profile.vehicle_color,
        driver_license_plate=profile.license_plate, status="OPEN", created_at=now,
    )


def build_request(index: int, owner: User, profile: DriverProfile,
                  locations: dict[str, PostLocationFields], now: datetime) -> RideRequest:
    pickup, dropoff, days, hour, passengers, bags, amount = REQUESTS[index]
    start, end = pickup_window(now, days, hour, (30, 60, 120)[index % 3])
    data = RideRequestInput.model_validate({
        "pickup_location_id": locations[pickup].location_id,
        "dropoff_location_id": locations[dropoff].location_id,
        "pickup_start": start, "pickup_end": end, "timezone": TIMEZONE,
        "passengers": passengers, "bags": bags, "preferred_amount": amount, "currency": "USD",
        "rider_phone": profile.phone, "exact_location_consent": True,
        "notes": f"{LABEL} request. {pickup} to {dropoff}. Public landmarks only. "
                 "No transport is actually requested; do not send offers or payments.",
    })
    return RideRequest(
        id=sample_id(owner.id, "request", index), rider_id=owner.id,
        **route_fields(locations, pickup, dropoff),
        pickup_start=utc_naive(data.pickup_start), pickup_end=utc_naive(data.pickup_end),
        timezone=data.timezone, passengers=data.passengers, bags=data.bags,
        notes=data.notes, rider_phone=data.rider_phone, currency=data.currency,
        preferred_amount=data.preferred_amount, status="OPEN", created_at=now,
    )


def seed_rides(db: Session, owner: User) -> tuple[int, int, int, int]:
    """Flush samples; the caller must own the transaction and commit atomically."""
    profile = require_existing_profile(db, owner)
    missing = {}
    for kind, model, owner_field, cases in (
        ("carpool", CarpoolTrip, CarpoolTrip.driver_id, CARPOOLS),
        ("request", RideRequest, RideRequest.rider_id, REQUESTS),
    ):
        ids = [sample_id(owner.id, kind, index) for index in range(len(cases))]
        existing = list(db.execute(select(model.id, owner_field).where(model.id.in_(ids))))
        if any(row[1] != owner.id for row in existing):
            raise RuntimeError("Sample ID belongs to another user; refusing to modify any data.")
        existing_ids = {row[0] for row in existing}
        missing[kind] = [index for index, id_ in enumerate(ids) if id_ not in existing_ids]
    needed = {area for kind, cases in (("carpool", CARPOOLS), ("request", REQUESTS))
              for index in missing[kind] for area in cases[index][:2]}
    locations = resolve_locations(needed)
    now = utc_now_naive()
    for index in missing["carpool"]:
        trip = build_trip(index, owner, profile, locations, now)
        if trip.outbound_id is not None:
            outbound = db.get(CarpoolTrip, trip.outbound_id)
            if (outbound is None or trip.pickup_start <= outbound.pickup_end
                    or trip.pickup["location_id"] != outbound.dropoff["location_id"]
                    or trip.dropoff["location_id"] != outbound.pickup["location_id"]):
                raise RuntimeError("Existing outbound no longer matches the missing demo return; nothing committed.")
        db.add(trip)
        db.flush()  # Insert the outbound before its self-referencing return.
    for index in missing["request"]:
        db.add(build_request(index, owner, profile, locations, now))
    db.flush()
    trips, requests = len(missing["carpool"]), len(missing["request"])
    return trips, len(CARPOOLS) - trips, requests, len(REQUESTS) - requests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Existing local owner with a completed real driver profile")
    args = parser.parse_args()
    url = parse_database_url(settings.DATABASE_URL)
    validate_local_database(url)
    engine = create_engine(url)
    try:
        with Session(engine) as db, db.begin():
            validate_migrations(db)
            owner = db.scalar(select(User).where(
                func.lower(User.email) == args.email.strip().lower(),
            ).with_for_update())
            if owner is None:
                raise RuntimeError("The requested user does not exist. Sign in locally first.")
            created_trips, skipped_trips, created_requests, skipped_requests = seed_rides(db, owner)
        print(f"Carpools: {created_trips} inserted, {skipped_trips} existing samples preserved.")
        print(f"Ride requests: {created_requests} inserted, {skipped_requests} existing samples preserved.")
        print("Fictional Bay Area/LA samples only. No profiles, other users, offers, seat requests or bookings modified.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from None
