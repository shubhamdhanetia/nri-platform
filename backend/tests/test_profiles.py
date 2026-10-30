import unittest
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.api.users import router
from app.db.base import Base
from app.db.dependencies import get_db
from app.models.post import Post, PostCategory, PostType
from app.models.user import User


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.owner_id, self.visitor_id = uuid4(), uuid4()
        with Session(self.engine) as db:
            for user_id, name in ((self.owner_id, "Owner"), (self.visitor_id, "Visitor")):
                db.add(User(
                    id=user_id, name=name, email=f"{name}@example.test",
                    provider="test", provider_id=name, created_at=datetime(2026, 10, 17, 12, 30),
                ))
            db.commit()
            self.visitor = db.get(User, self.visitor_id)
            db.expunge(self.visitor)
        self.app = FastAPI()
        self.app.include_router(router, prefix="/users")

        def test_db():
            with Session(self.engine) as db:
                yield db

        self.app.dependency_overrides[get_db] = test_db
        self.app.dependency_overrides[get_current_user] = lambda: self.visitor
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_profile_is_member_only_and_omits_private_fields(self):
        response = self.client.get(f"/users/{self.owner_id}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(set(response.json()), {"id", "name", "picture", "member_since", "bio", "home_city", "languages"})
        self.assertEqual(response.json()["member_since"], "2026-10-01")
        self.app.dependency_overrides.pop(get_current_user)
        for path in (f"/users/{self.owner_id}", f"/users/{self.owner_id}/posts", "/users/me"):
            self.assertIn(self.client.get(path).status_code, (401, 403))
        self.assertIn(self.client.patch("/users/me", json={"bio": "No"}).status_code, (401, 403))

    def test_updates_only_current_member_and_normalizes_optional_fields(self):
        response = self.client.patch("/users/me", json={
            "bio": " Hello ", "home_city": " Fremont ", "languages": [" English ", "english", "Hindi"],
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["languages"], ["English", "Hindi"])
        self.assertEqual(response.json()["bio"], "Hello")
        self.assertEqual(response.json()["home_city"], "Fremont")
        with Session(self.engine) as db:
            self.assertIsNone(db.get(User, self.owner_id).bio)
            self.assertEqual(db.get(User, self.visitor_id).bio, "Hello")
        cleared = self.client.patch("/users/me", json={"bio": " ", "languages": []}).json()
        self.assertIsNone(cleared["bio"])
        self.assertEqual(cleared["languages"], [])
        self.assertEqual(cleared["home_city"], "Fremont")
        self.assertEqual(self.client.patch(f"/users/{self.owner_id}", json={"bio": "No"}).status_code, 405)

    def test_validation_and_unknown_profiles(self):
        for payload in ({"bio": "x" * 161}, {"home_city": "x" * 101}, {"languages": [" "]},
                        {"languages": ["x" * 51]}, {"languages": [str(index) for index in range(11)]},
                        {"languages": None}, {"name": "Changed"}, {"id": str(self.owner_id)}, {"email": "new@example.test"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.patch("/users/me", json=payload).status_code, 422)
        for suffix in ("", "/posts"):
            self.assertEqual(self.client.get(f"/users/{uuid4()}{suffix}").status_code, 404)
            self.assertEqual(self.client.get(f"/users/not-a-uuid{suffix}").status_code, 422)
        for query in ("limit=51", "limit=0", "offset=-1"):
            self.assertEqual(self.client.get(f"/users/{self.owner_id}/posts?{query}").status_code, 422)

    def test_posts_filter_visibility_and_owner_before_pagination(self):
        with Session(self.engine) as db:
            for index in range(1, 5):
                db.add(Post(
                    id=UUID(int=index), user_id=self.visitor_id if index == 4 else self.owner_id,
                    title=f"Post {index}", description="Community news", category=PostCategory.GENERAL,
                    post_type=PostType.DISCUSSION, is_private=index == 3,
                    location_id="test", location="Private street address", country_code="US",
                    postal_code="94538", state="CA", city="Fremont", latitude=37.55,
                    longitude=-121.98, h3_cell_id="test", created_at=datetime(2026, 10, 28),
                ))
            db.commit()
        first = self.client.get(f"/users/{self.owner_id}/posts?limit=1").json()
        second = self.client.get(f"/users/{self.owner_id}/posts?limit=1&offset=1").json()
        self.assertTrue(first["has_more"])
        self.assertFalse(second["has_more"])
        self.assertEqual(first["posts"][0]["id"], str(UUID(int=2)))
        self.assertEqual(second["posts"][0]["id"], str(UUID(int=1)))
        self.assertNotIn("location", first["posts"][0])
        self.assertNotIn("latitude", first["posts"][0])
        with Session(self.engine) as db:
            owner = db.get(User, self.owner_id)
            db.expunge(owner)
        self.app.dependency_overrides[get_current_user] = lambda: owner
        own_preview = self.client.get(f"/users/{self.owner_id}/posts").json()
        self.assertEqual(len(own_preview["posts"]), 2)