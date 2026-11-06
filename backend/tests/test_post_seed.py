import unittest
from unittest.mock import patch
from uuid import uuid4

import h3
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.ride_time import utc_now_naive
from app.db.base import Base
from app.models.post import Post, PostCategory, PostStatus, PostType
from app.models.user import User
from app.schemas.location import LocationSearchResponse
from app.schemas.post import PostLocationFields
from scripts.seed_posts import LOCATIONS, POST_COUNT, build_sample, sample_id, seed_posts


class PostSeedTests(unittest.TestCase):
    def setUp(self):
        self.owner_id = uuid4()
        self.locations = {
            area: PostLocationFields(
                location_id=f"test-{area.lower().replace(' ', '-')}",
                location=f"Public landmark, {area}, CA", city=area, state="CA",
                country_code="US", postal_code="90000", latitude=latitude,
                longitude=longitude, h3_cell_id=h3.latlng_to_cell(latitude, longitude, 8),
            )
            for area, _, latitude, longitude in LOCATIONS
        }

    def test_samples_cover_categories_post_types_and_both_regions(self):
        posts = [build_sample(index, self.owner_id, self.locations, utc_now_naive()) for index in range(POST_COUNT)]
        self.assertEqual(len({post.id for post in posts}), POST_COUNT)
        self.assertEqual({post.category for post in posts}, set(PostCategory))
        self.assertEqual({post.post_type for post in posts}, set(PostType))
        self.assertEqual({post.city for post in posts} & {"Fremont", "San Jose", "Oakland", "San Francisco", "Berkeley", "San Mateo"},
                         {"Fremont", "San Jose", "Oakland", "San Francisco", "Berkeley", "San Mateo"})
        self.assertTrue({post.city for post in posts} & {"Los Angeles", "Pasadena", "Long Beach", "Santa Monica", "Glendale"})
        self.assertTrue(all(
            post.title.startswith("[Demo]") and any(
                marker in post.description
                for marker in ("SAMPLE DATA ONLY", "DEMO POST", "Fictional sample", "SAMPLE CONTENT")
            )
            for post in posts
        ))
        self.assertTrue(all(post.is_private is False and post.status == PostStatus.ACTIVE for post in posts))

    def test_seed_is_repeatable_and_preserves_existing_post_edits(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)

        def search(request):
            area, _, _, _ = next(item for item in LOCATIONS if item[1] == request.query)
            return LocationSearchResponse(status="success", data=[{"id": area, "addressLine1": request.query}])

        with Session(engine) as db:
            owner = User(id=self.owner_id, name="Demo owner", email="demo@example.test", provider="test", provider_id="demo")
            db.add(owner)
            db.commit()
            with patch("scripts.seed_posts.search_locations", side_effect=search), patch(
                "scripts.seed_posts.resolve_post_location", side_effect=self.locations.__getitem__,
            ):
                self.assertEqual(seed_posts(db, owner), (POST_COUNT, 0))
            first = db.get(Post, sample_id(owner.id, 0))
            first.title = "Owner-edited sample"
            db.commit()
            with patch("scripts.seed_posts.search_locations") as search_mock:
                self.assertEqual(seed_posts(db, owner), (0, POST_COUNT))
                search_mock.assert_not_called()
            self.assertEqual(db.get(Post, first.id).title, "Owner-edited sample")
            self.assertEqual(len(list(db.scalars(select(Post)))), POST_COUNT)

    def test_location_provider_failure_inserts_nothing(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            owner = User(id=self.owner_id, name="Demo owner", email="demo@example.test", provider="test", provider_id="demo")
            db.add(owner)
            db.commit()
            with patch("scripts.seed_posts.search_locations", return_value=LocationSearchResponse(status="success", data=[])):
                with self.assertRaisesRegex(RuntimeError, "nothing has been committed"):
                    seed_posts(db, owner)
            self.assertEqual(list(db.scalars(select(Post))), [])