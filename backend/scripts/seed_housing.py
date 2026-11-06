"""Insert clearly labelled, repeatable Housing demo posts into localhost only."""

import argparse
from collections import Counter
from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.main import app as _app  # Registers all related ORM models.
from app.core.config import settings
from app.core.ride_time import utc_now_naive
from app.db.url import parse_database_url
from app.models.housing import HousingPost
from app.models.user import User
from app.schemas.housing import HousingContent
from app.schemas.location import LocationSearchRequest
from app.schemas.post import PostLocationFields
from app.services.location_search import resolve_post_location, search_locations


LOCATIONS = (
    ("Fremont", "Fremont BART Station, Fremont California", 37.557, -121.976),
    ("San Jose", "San Jose Diridon Station California", 37.330, -121.902),
    ("Sunnyvale", "Sunnyvale Caltrain Station California", 37.378, -122.030),
    ("San Francisco", "San Francisco Ferry Building California", 37.795, -122.393),
    ("Oakland", "Lake Merritt Oakland California", 37.804, -122.258),
    ("Berkeley", "Downtown Berkeley BART Station California", 37.870, -122.268),
    ("Long Beach downtown", "Long Beach Convention Center California", 33.766, -118.189),
    ("Belmont Shore", "Belmont Shore Long Beach California", 33.759, -118.133),
    ("Bixby Knolls", "Bixby Knolls Long Beach California", 33.831, -118.184),
)

# Public landmark coordinates are demo anchors, never claims of real availability.
CASES = (
    ("Fremont", "Vegetarian private room near BART", "LISTING", "PRIVATE", "HOUSEHOLD", "LONG_TERM", "MONTH", 1150),
    ("San Jose", "Shared room with eggs-allowed kitchen", "LISTING", "SHARED", "HOUSEHOLD", "LONG_TERM", "MONTH", 750),
    ("Sunnyvale", "Furnished family rental", "LISTING", "ENTIRE", "RENTAL", "LONG_TERM", "MONTH", 3400),
    ("San Francisco", "Two-week furnished sublet", "LISTING", "PRIVATE", "SUBLET", "SHORT_TERM", "WEEK", 550),
    ("Oakland", "Apartment lease takeover", "LISTING", "ENTIRE", "TAKEOVER", "LONG_TERM", "MONTH", 2450),
    ("Berkeley", "Temporary guest stay", "LISTING", "PRIVATE", "SUBLET", "SHORT_TERM", "NIGHT", 85),
    ("Fremont", "Looking for a private room", "REQUEST", "PRIVATE", "ANY", "LONG_TERM", "MONTH", 1300),
    ("San Jose", "Flexible shared-room budget", "REQUEST", "SHARED", "HOUSEHOLD", "FLEXIBLE", "MONTH", 800),
    ("Sunnyvale", "Family looking for an entire home", "REQUEST", "ENTIRE", "RENTAL", "LONG_TERM", "MONTH", 3800),
    ("San Francisco", "Looking for a short weekly stay", "REQUEST", "ANY", "SUBLET", "SHORT_TERM", "WEEK", 650),
    ("Oakland", "Find a vegetarian household together", "TOGETHER", "PRIVATE", "ANY", "LONG_TERM", "MONTH", 1400),
    ("Berkeley", "Search together near transit", "TOGETHER", "ANY", "RENTAL", "FLEXIBLE", "MONTH", 1200),
    ("Long Beach downtown", "Private room near downtown", "LISTING", "PRIVATE", "HOUSEHOLD", "LONG_TERM", "MONTH", 1050),
    ("Belmont Shore", "Shared room with beach commute", "LISTING", "SHARED", "HOUSEHOLD", "FLEXIBLE", "MONTH", 700),
    ("Bixby Knolls", "Entire rental with parking", "LISTING", "ENTIRE", "RENTAL", "LONG_TERM", "MONTH", 2900),
    ("Long Beach downtown", "Weekend temporary stay", "LISTING", "PRIVATE", "SUBLET", "SHORT_TERM", "NIGHT", 95),
    ("Belmont Shore", "Lease takeover with approval pending", "LISTING", "ENTIRE", "TAKEOVER", "LONG_TERM", "MONTH", 2600),
    ("Bixby Knolls", "Looking for a quiet room", "REQUEST", "PRIVATE", "ANY", "LONG_TERM", "MONTH", 1100),
    ("Long Beach downtown", "Find an apartment together", "TOGETHER", "ANY", "RENTAL", "LONG_TERM", "MONTH", 1500),
    ("Belmont Shore", "Weekly sublet wanted", "REQUEST", "ANY", "SUBLET", "SHORT_TERM", "WEEK", 450),
    ("Fremont", "Filled room lifecycle example", "LISTING", "PRIVATE", "HOUSEHOLD", "LONG_TERM", "MONTH", 1000),
    ("Long Beach downtown", "Archived rental lifecycle example", "LISTING", "ENTIRE", "RENTAL", "LONG_TERM", "MONTH", 2800),
    ("San Jose", "Private draft visibility example", "REQUEST", "ANY", "ANY", "FLEXIBLE", "MONTH", 1250),
    ("Bixby Knolls", "Expired post lifecycle example", "LISTING", "PRIVATE", "HOUSEHOLD", "LONG_TERM", "MONTH", 950),
    ("Oakland", "Stay dates ended example", "LISTING", "SHARED", "SUBLET", "SHORT_TERM", "WEEK", 300),
    ("Belmont Shore", "Filled search-together example", "TOGETHER", "ANY", "ANY", "FLEXIBLE", "MONTH", 1300),
)
PHOTOS = (
    "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=1000&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=1000&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1000&auto=format&fit=crop&q=80",
)


def sample_id(owner_id: UUID, index: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"nri-platform:housing-demo:v1:{owner_id}:{index}")


def build_sample(index: int, owner_id: UUID, location: PostLocationFields, now: datetime) -> HousingPost:
    area, title, kind, room, arrangement, stay, period, amount = CASES[index]
    minimum = 2 if stay == "SHORT_TERM" else 30
    start = now.date() + timedelta(days=index % 10)
    end = start + timedelta(days=14) if stay == "SHORT_TERM" else None
    if index == 24:
        start, end = now.date() - timedelta(days=20), now.date() - timedelta(days=2)
    content = HousingContent.model_validate({
        "title": f"[Demo] {title}",
        "description": (
            f"SAMPLE DATA ONLY - not a real housing offer or request. {title} in {area}. "
            "The map point is a public neighborhood landmark, not a residential address. "
            "Photos are illustrative stock images, not this property. "
            "Use this post to explore filters and inquiries; do not send money or visit expecting accommodation."
        ),
        "kind": kind, "room_type": room, "arrangement": arrangement, "stay_type": stay,
        "area": f"{area} - demo landmark anchor", "amount": amount, "currency": "USD",
        "price_period": period, "available_from": start, "available_until": end,
        "minimum_stay_days": minimum, "available_spaces": 2 if room == "SHARED" else 1,
        "occupants": index % 4, "furnishing": ("FURNISHED", "PARTLY", "UNFURNISHED", "UNSPECIFIED")[index % 4],
        "bathroom": ("PRIVATE", "SHARED", "UNSPECIFIED")[index % 3],
        "utilities": ("INCLUDED", "EXTRA", "PARTLY", "UNKNOWN")[index % 4],
        "deposit": 0 if stay == "SHORT_TERM" else amount, "fees": 50 if index % 3 == 0 else None,
        "approval": ("REQUIRED", "PENDING", "OBTAINED")[index % 3] if arrangement in ("SUBLET", "TAKEOVER") else "NOT_APPLICABLE",
        "kitchen": ("VEGETARIAN", "EGGS_ALLOWED", "UNRESTRICTED", "UNSPECIFIED")[index % 4],
        "smoking": ("NO", "OUTSIDE", "YES", "UNSPECIFIED")[index % 4],
        "alcohol": ("NO", "YES", "UNSPECIFIED")[index % 3],
        "pets": ("NO", "ALLOWED", "PRESENT", "UNSPECIFIED")[index % 4],
        "parking": (True, False, None)[index % 3], "laundry": (False, True, None)[index % 3],
        "kitchen_access": True, "work_from_home": index % 2 == 0,
        "household_notes": "Demo household details only. Discuss routines and shared responsibilities directly.",
        "accessibility_notes": "Demo: confirm step-free access and other requirements before arranging a visit.",
        "photo_urls": [PHOTOS[index % len(PHOTOS)], PHOTOS[(index + 1) % len(PHOTOS)]],
        "is_private": index == 22,
    })
    return HousingPost(
        id=sample_id(owner_id, index), owner_id=owner_id,
        **content.model_dump(), **location.model_dump(),
        status="FILLED" if index in (20, 25) else "ARCHIVED" if index == 21 else "ACTIVE",
        created_at=now - timedelta(minutes=index), expires_at=now + timedelta(days=-1 if index == 23 else 30),
    )


def seed_housing(db: Session, owner: User) -> tuple[int, int]:
    existing = set(db.scalars(select(HousingPost.id).where(
        HousingPost.id.in_([sample_id(owner.id, index) for index in range(len(CASES))]),
    )))
    missing = [index for index in range(len(CASES)) if sample_id(owner.id, index) not in existing]
    locations: dict[str, PostLocationFields] = {}
    needed = {CASES[index][0] for index in missing}
    for area, query, latitude, longitude in LOCATIONS:
        if area not in needed:
            continue
        suggestions = search_locations(LocationSearchRequest(query=query, latitude=latitude, longitude=longitude))
        suggestion = next((item for item in suggestions.data if item.id), None)
        if suggestion is None or suggestion.id is None:
            raise RuntimeError(f"No provider location found for {area}; nothing has been committed.")
        location = resolve_post_location(suggestion.id)
        if (location.country_code != "US" or abs(location.latitude - latitude) > 0.15
                or abs(location.longitude - longitude) > 0.15):
            raise RuntimeError(f"Provider returned an unexpected location for {area}; nothing has been committed.")
        locations[area] = location
    now = utc_now_naive()
    for index in missing:
        db.add(build_sample(index, owner.id, locations[CASES[index][0]], now))
    db.commit()
    return len(missing), len(existing)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Existing local user to own demo posts")
    args = parser.parse_args()
    url = parse_database_url(settings.DATABASE_URL)
    if url.host not in ("localhost", "127.0.0.1", "::1") or url.get_backend_name() != "postgresql":
        raise SystemExit("Refusing to seed: this command only supports local PostgreSQL.")
    engine = create_engine(url)
    try:
        with Session(engine) as db:
            if db.scalar(text("SELECT version_num FROM alembic_version")) != "0015":
                raise SystemExit("Apply migrations through 0015 before seeding.")
            owner = db.scalar(select(User).where(func.lower(User.email) == args.email.strip().lower()))
            if owner is None:
                raise SystemExit("The requested user does not exist. Sign in locally first.")
            created, skipped = seed_housing(db, owner)
            print(f"Housing demo posts: {created} inserted, {skipped} existing samples preserved.")
            print("Kinds:", dict(Counter(case[2] for case in CASES)))
            print("Regions: Bay Area and Long Beach. No other accounts or posts were modified.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
