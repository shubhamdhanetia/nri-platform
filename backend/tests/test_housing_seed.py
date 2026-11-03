import unittest
from unittest.mock import patch
from uuid import uuid4

import h3
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.ride_time import utc_now_naive
from app.db.base import Base
from app.models.housing import HousingPost
from app.models.user import User
from app.schemas.housing import HousingResponse
from app.schemas.location import LocationSearchResponse
from app.schemas.post import PostLocationFields
from scripts.seed_housing import CASES, LOCATIONS, build_sample, sample_id, seed_housing


class HousingSeedTests(unittest.TestCase):
    def setUp(self):
        self.owner_id = uuid4()
        self.now = utc_now_naive()
        self.location = PostLocationFields(
            location_id="test-place", location="Public test landmark, Fremont, CA",
            city="Fremont", state="CA", country_code="US", postal_code="94538",
            latitude=37.557, longitude=-121.976,
            h3_cell_id=h3.latlng_to_cell(37.557, -121.976, 8),
        )

    def test_samples_cover_types_filters_photos_and_lifecycles(self):
        posts = [build_sample(index, self.owner_id, self.location, self.now) for index in range(len(CASES))]
        self.assertEqual(len({post.id for post in posts}), len(CASES))
        for field, expected in (
            ("kind", {"LISTING", "REQUEST", "TOGETHER"}),
            ("room_type", {"SHARED", "PRIVATE", "ENTIRE", "ANY"}),
            ("arrangement", {"HOUSEHOLD", "RENTAL", "SUBLET", "TAKEOVER", "ANY"}),
            ("stay_type", {"SHORT_TERM", "LONG_TERM", "FLEXIBLE"}),
            ("price_period", {"MONTH", "WEEK", "NIGHT"}),
            ("kitchen", {"VEGETARIAN", "EGGS_ALLOWED", "UNRESTRICTED", "UNSPECIFIED"}),
            ("status", {"ACTIVE", "FILLED", "ARCHIVED"}),
        ):
            self.assertEqual({getattr(post, field) for post in posts}, expected)
        self.assertEqual(sum(post.is_private for post in posts), 1)
        self.assertEqual(sum(post.expires_at < self.now for post in posts), 1)
        self.assertEqual(sum(post.available_until is not None and post.available_until < self.now.date() for post in posts), 1)
        self.assertEqual({case[0] for case in CASES}, {location[0] for location in LOCATIONS})
        for post in posts:
            post.owner = User(id=self.owner_id, name="Test owner")
            post.updated_at = None
            response = HousingResponse.model_validate(post)
            self.assertEqual(len(response.photo_urls), 2)
            self.assertTrue(response.title.startswith("[Demo]"))
            self.assertIn("not a real", response.description)
            self.assertEqual(post.h3_cell_id, h3.latlng_to_cell(post.latitude, post.longitude, 8))

    def test_repeat_seed_preserves_existing_owner_edits(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)

        def resolve(location_id):
            _, latitude, longitude = location_id.split("|")
            lat, lng = float(latitude), float(longitude)
            return self.location.model_copy(update={
                "location_id": location_id, "latitude": lat, "longitude": lng,
                "h3_cell_id": h3.latlng_to_cell(lat, lng, 8),
            })

        def search(request):
            return LocationSearchResponse(status="success", data=[{
                "id": f"test|{request.latitude}|{request.longitude}", "addressLine1": request.query,
            }])

        with Session(engine) as db:
            owner = User(id=self.owner_id, name="Demo owner", email="demo@example.test", provider="test", provider_id="demo")
            db.add(owner)
            db.commit()
            with patch("scripts.seed_housing.search_locations", side_effect=search), patch("scripts.seed_housing.resolve_post_location", side_effect=resolve):
                self.assertEqual(seed_housing(db, owner), (len(CASES), 0))
            first = db.get(HousingPost, sample_id(owner.id, 0))
            first.title = "[Demo] Owner edited title"
            db.commit()
            with patch("scripts.seed_housing.search_locations") as search_mock:
                self.assertEqual(seed_housing(db, owner), (0, len(CASES)))
                search_mock.assert_not_called()
            self.assertEqual(db.get(HousingPost, first.id).title, "[Demo] Owner edited title")
            self.assertEqual(len(list(db.scalars(select(HousingPost)))), len(CASES))

    def test_provider_failure_does_not_insert_partial_samples(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            owner = User(id=self.owner_id, name="Demo owner", email="demo@example.test", provider="test", provider_id="demo")
            db.add(owner)
            db.commit()
            with patch("scripts.seed_housing.search_locations", return_value=LocationSearchResponse(status="success", data=[])):
                with self.assertRaisesRegex(RuntimeError, "nothing has been committed"):
                    seed_housing(db, owner)
            self.assertEqual(list(db.scalars(select(HousingPost))), [])
