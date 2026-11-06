"""Insert 100 clearly labelled, repeatable community demo posts into localhost only."""

import argparse
from collections import Counter
from datetime import timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.main import app as _app  # Registers all related ORM models.
from app.core.config import settings
from app.core.ride_time import utc_now_naive
from app.db.url import parse_database_url
from app.models.post import Post, PostCategory, PostStatus, PostType
from app.models.user import User
from app.schemas.location import LocationSearchRequest
from app.schemas.post import PostLocationFields
from app.services.location_search import resolve_post_location, search_locations


LOCATIONS = (
    ("Fremont", "Fremont BART Station California", 37.557, -121.976),
    ("San Jose", "San Jose Diridon Station California", 37.330, -121.902),
    ("Oakland", "Lake Merritt Oakland California", 37.804, -122.258),
    ("San Francisco", "San Francisco Ferry Building California", 37.795, -122.393),
    ("Berkeley", "Downtown Berkeley BART Station California", 37.870, -122.268),
    ("San Mateo", "San Mateo Caltrain Station California", 37.568, -122.324),
    ("Los Angeles", "Union Station Los Angeles California", 34.056, -118.236),
    ("Pasadena", "Pasadena City Hall California", 34.147, -118.144),
    ("Long Beach", "Long Beach Convention Center California", 33.766, -118.189),
    ("Santa Monica", "Santa Monica Pier California", 34.009, -118.497),
    ("Glendale", "Glendale Americana California", 34.145, -118.257),
)

TITLES = {
    PostCategory.HOUSING: ("Room near transit", "Looking for a shared apartment", "Furnished short stay", "Roommate search"),
    PostCategory.HOUSEHOLD_HELP: ("Seeking a weekly home cleaner", "Part-time cooking help wanted", "Offering household cleaning help", "Looking for an occasional helper"),
    PostCategory.TRAVEL: ("Weekend trip recommendations", "Looking for airport travel tips", "Sharing a day-trip idea", "Seeking a travel companion for a public event"),
    PostCategory.RIDES_CARPOOL: ("Commuter carpool seats available", "Looking for a weekday ride share", "Airport carpool discussion", "Offering a weekend carpool"),
    PostCategory.PARKING: ("Monthly parking spot available", "Looking for a secure parking space", "Visitor parking recommendations", "Parking spot sharing inquiry"),
    PostCategory.JOBS: ("Part-time role information", "Seeking local work leads", "Sharing a community job opening", "Looking for weekend work"),
    PostCategory.FOOD: ("Favorite lunch spots nearby", "Looking for vegetarian meal ideas", "Sharing a home-cooking recommendation", "Community potluck discussion"),
    PostCategory.EVENTS: ("Neighborhood event this weekend", "Looking for family-friendly events", "Sharing a local cultural meetup", "Community event recommendations"),
    PostCategory.SPORTS: ("Weekend soccer players wanted", "Looking for a local tennis group", "Sharing a community hike", "Pickup basketball discussion"),
    PostCategory.IMMIGRATION: ("Seeking a visa-resource recommendation", "Sharing a community information session", "Looking for a local immigration clinic", "Question about trusted settlement resources"),
    PostCategory.MARKETPLACE: ("Household items available", "Looking for a used bicycle", "Community swap recommendations", "Small appliance giveaway"),
    PostCategory.MEDICAL_SUPPORT: ("Looking for a nearby clinic recommendation", "Sharing public health resource information", "Seeking a caregiver resource referral", "Community wellness support discussion"),
    PostCategory.GENERAL: ("New to the neighborhood", "Looking for local recommendations", "Community question", "Sharing a neighborhood tip"),
}

DESCRIPTIONS = (
    "SAMPLE DATA ONLY. This fictional example is for exploring community categories and location search; it is not a real offer, request, or event. Do not travel, pay, or share personal information based on this post.",
    "DEMO POST - not a real listing or request. The map location is a public landmark used only to demonstrate discovery. Please use real posts and verify details independently.",
    "Fictional sample for interface testing only. No service, job, housing, ride, event, or item is actually being offered. The location is an approximate public-area anchor.",
    "SAMPLE CONTENT for previewing the community feed. This is not a real person or opportunity, and the location is not a home or meeting address.",
)

POST_COUNT = 100


def sample_id(owner_id: UUID, index: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"nri-platform:community-post-demo:v1:{owner_id}:{index}")


def build_sample(index: int, owner_id: UUID, locations: dict[str, PostLocationFields], now):
    area = LOCATIONS[index % len(LOCATIONS)][0]
    category = list(PostCategory)[index % len(PostCategory)]
    title_options = TITLES[category]
    title = title_options[(index // len(PostCategory)) % len(title_options)]
    post_type = list(PostType)[(index // 2 + index % len(LOCATIONS)) % len(PostType)]
    created_at = now - timedelta(hours=index * 11)
    return Post(
        id=sample_id(owner_id, index),
        user_id=owner_id,
        title=f"[Demo] {title} - {area}",
        description=f"{DESCRIPTIONS[index % len(DESCRIPTIONS)]} Area: {area}.",
        category=category,
        post_type=post_type,
        status=PostStatus.ACTIVE,
        is_private=False,
        **locations[area].model_dump(),
        created_at=created_at,
    )


def seed_posts(db: Session, owner: User) -> tuple[int, int]:
    ids = [sample_id(owner.id, index) for index in range(POST_COUNT)]
    existing = set(db.scalars(select(Post.id).where(Post.id.in_(ids))))
    missing = [index for index, post_id in enumerate(ids) if post_id not in existing]
    needed = {LOCATIONS[index % len(LOCATIONS)][0] for index in missing}
    locations: dict[str, PostLocationFields] = {}
    for area, query, latitude, longitude in LOCATIONS:
        if area not in needed:
            continue
        suggestions = search_locations(LocationSearchRequest(
            query=query, latitude=latitude, longitude=longitude,
        ))
        suggestion = next((item for item in suggestions.data if item.id), None)
        if suggestion is None or suggestion.id is None:
            raise RuntimeError(f"No provider location found for {area}; nothing has been committed.")
        location = resolve_post_location(suggestion.id)
        if (location.country_code != "US" or abs(location.latitude - latitude) > 0.2
                or abs(location.longitude - longitude) > 0.2):
            raise RuntimeError(f"Provider returned an unexpected location for {area}; nothing has been committed.")
        locations[area] = location

    now = utc_now_naive()
    for index in missing:
        db.add(build_sample(index, owner.id, locations, now))
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
            if db.scalar(text("SELECT version_num FROM alembic_version")) != "0013":
                raise SystemExit("Apply migrations through 0013 before seeding.")
            owner = db.scalar(select(User).where(func.lower(User.email) == args.email.strip().lower()))
            if owner is None:
                raise SystemExit("The requested user does not exist. Sign in locally first.")
            created, skipped = seed_posts(db, owner)
            print(f"Community demo posts: {created} inserted, {skipped} existing samples preserved.")
            print("Categories:", dict(Counter(list(PostCategory)[index % len(PostCategory)].value for index in range(POST_COUNT))))
            print("Regions: Bay Area and Los Angeles. All posts are public, fictional samples at public landmarks.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()