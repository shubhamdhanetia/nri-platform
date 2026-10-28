import unittest
from datetime import datetime
from unittest.mock import patch

import h3
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.api.posts import router
from app.db.base import Base
from app.db.dependencies import get_db
from app.models.post import Post, PostCategory, PostType
from app.models.user import User
from app.schemas.post import PostLocationFields
from app.services.post_search import h3_cells_for_bounds


class PostSearchTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.user = User(id=1, name="Member", email="member@example.test", provider="test", provider_id="1")
        with Session(self.engine) as db:
            db.add(self.user)
            db.commit()
            db.refresh(self.user)
            db.expunge(self.user)
        app = FastAPI()
        app.include_router(router, prefix="/posts")

        def test_db():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.bounds = {"north": 37.56, "south": 37.54, "east": -121.97, "west": -121.99}

    def seed(self, post_id, **updates):
        values = dict(
            id=post_id, title=f"Post {post_id}", description="Community news",
            category=PostCategory.GENERAL, post_type=PostType.DISCUSSION,
            is_private=False, location_id="test", location="Fremont, CA",
            country_code="US", postal_code="94538", state="CA", city="Fremont",
            latitude=37.55, longitude=-121.98,
            h3_cell_id=h3.latlng_to_cell(37.55, -121.98, 8), user_id=1,
            created_at=datetime(2026, 10, 27),
        )
        values.update(updates)
        with Session(self.engine) as db:
            db.add(Post(**values))
            db.commit()

    def search(self, **payload):
        response = self.client.post("/posts/search", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_global_search_is_bounded_and_paginated(self):
        for post_id in range(1, 54):
            self.seed(post_id, is_private=post_id == 53)
        with patch("app.api.posts.h3_cells_for_bounds") as cells:
            first = self.search()
            second = self.search(offset=50)
            cells.assert_not_called()
        self.assertEqual([post["id"] for post in first["posts"]], list(range(52, 2, -1)))
        self.assertTrue(first["has_more"])
        self.assertEqual([post["id"] for post in second["posts"]], [2, 1])
        self.assertFalse(second["has_more"])

    def test_area_search_uses_h3_and_exact_bounds(self):
        self.seed(1)
        self.seed(2, latitude=40, longitude=-73, h3_cell_id=h3.latlng_to_cell(40, -73, 8))
        self.seed(3, h3_cell_id=h3.latlng_to_cell(40, -73, 8))
        self.seed(4, latitude=40)
        self.seed(5, is_private=True)
        with patch("app.api.posts.h3_cells_for_bounds", wraps=h3_cells_for_bounds) as cells:
            result = self.search(bounds=self.bounds)
            cells.assert_called_once()
        self.assertEqual([post["id"] for post in result["posts"]], [1])

    def test_filters_apply_before_limit_and_escape_wildcards(self):
        self.seed(1, title="50% discount", category=PostCategory.FOOD, post_type=PostType.OFFER)
        self.seed(2, title="50 percent discount", category=PostCategory.FOOD, post_type=PostType.OFFER)
        self.seed(3, title="50% discount", category=PostCategory.FOOD)
        self.seed(4, title="50% discount", post_type=PostType.OFFER)
        for bounds in (None, self.bounds):
            with self.subTest(bounds=bounds):
                result = self.search(bounds=bounds, category="FOOD", post_type="OFFER", query="50% DISCOUNT", limit=1)
                self.assertEqual([post["id"] for post in result["posts"]], [1])
                self.assertFalse(result["has_more"])

    def test_invalid_limits_offsets_and_oversized_areas_are_rejected(self):
        for payload in ({"limit": 51}, {"limit": 0}, {"offset": -1}, {"query": "x" * 201},
                        {"bounds": {"north": 80, "south": -80, "east": 180, "west": -180}}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/posts/search", json=payload).status_code, 422)

    def test_medical_support_category_can_be_created_updated_and_searched(self):
        location = {
            "location_id": "test", "location": "Fremont, CA", "city": "Fremont",
            "country_code": "US", "postal_code": "94538", "state": "CA",
            "latitude": 37.55, "longitude": -121.98,
            "h3_cell_id": h3.latlng_to_cell(37.55, -121.98, 8),
        }
        payload = {
            "title": "Community caregiver resources", "description": "Local support resources",
            "category": "MEDICAL_SUPPORT", "post_type": "REQUEST", "location_id": "test",
        }
        with patch("app.api.posts.resolve_post_location", return_value=PostLocationFields(**location)):
            created = self.client.post("/posts", json=payload)
            self.assertEqual(created.status_code, 200, created.text)
            post_id = created.json()["id"]
            self.assertEqual(created.json()["category"], "MEDICAL_SUPPORT")
            for category in ("GENERAL", "MEDICAL_SUPPORT"):
                updated = self.client.put(
                    f"/posts/{post_id}", json={**payload, "category": category},
                )
                self.assertEqual(updated.status_code, 200, updated.text)
                self.assertEqual(updated.json()["category"], category)
        self.seed(post_id + 1)
        self.seed(post_id + 2, category=PostCategory.MEDICAL_SUPPORT, is_private=True)
        for bounds in (None, self.bounds):
            with self.subTest(bounds=bounds):
                result = self.search(bounds=bounds, category="MEDICAL_SUPPORT")
                self.assertEqual([post["id"] for post in result["posts"]], [post_id])
                self.assertEqual(result["posts"][0]["category"], "MEDICAL_SUPPORT")