from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.models.post import Post, PostCategory, PostStatus, PostType
from app.models.user import User
from app.repositories.post_repository import get_public_posts_by_user
from app.schemas.post import PostLocationFields
from tests import test_post_search


class PostLifecycleTests(test_post_search.PostSearchTests):
    def setUp(self):
        super().setUp()
        self.owner = self.user
        self.other = User(
            id=UUID(int=2), name="Reader", email="reader@example.test",
            provider="test", provider_id="reader",
        )
        with Session(self.engine) as db:
            db.add(self.other)
            db.commit()
            db.refresh(self.other)
            db.expunge(self.other)

    def status(self, post_id, status):
        return self.client.put(f"/posts/{UUID(int=post_id)}/status", json={"status": status})

    def test_close_reopen_all_categories_and_both_listing_types(self):
        for index, category in enumerate(PostCategory, start=1):
            for kind_index, post_type in enumerate((PostType.OFFER, PostType.REQUEST)):
                post_id = index * 10 + kind_index
                with self.subTest(category=category, post_type=post_type):
                    self.seed(post_id, category=category, post_type=post_type)
                    closed = self.status(post_id, "CLOSED")
                    self.assertEqual(closed.status_code, 200, closed.text)
                    self.assertEqual(closed.json()["status"], "CLOSED")
                    self.assertFalse(closed.json()["is_private"])
                    self.assertEqual(self.status(post_id, "CLOSED").status_code, 200)
                    for bounds in (None, self.bounds):
                        self.assertNotIn(str(UUID(int=post_id)), [
                            item["id"] for item in self.search(bounds=bounds)["posts"]
                        ])
                    self.assertNotIn(str(UUID(int=post_id)), [p["id"] for p in self.client.get("/posts").json()])
                    self.assertIn(str(UUID(int=post_id)), [p["id"] for p in self.client.get("/posts/me").json()])
                    self.assertEqual(self.client.get(f"/posts/{UUID(int=post_id)}").status_code, 200)
                    with Session(self.engine) as db:
                        self.assertNotIn(UUID(int=post_id), [
                            p.id for p in get_public_posts_by_user(db, self.owner.id, 50, 0)
                        ])
                    reopened = self.status(post_id, "ACTIVE")
                    self.assertEqual(reopened.status_code, 200, reopened.text)
                    self.assertEqual(reopened.json()["status"], "ACTIVE")
                    self.assertIn(str(UUID(int=post_id)), [p["id"] for p in self.search()["posts"]])

    def test_saved_closed_post_access_obeys_privacy_and_deletion(self):
        self.seed(1, post_type=PostType.REQUEST)
        path = f"/posts/{UUID(int=1)}"
        self.client.app.dependency_overrides[get_current_user] = lambda: self.other
        self.assertEqual(self.client.post(path + "/save").status_code, 200)
        self.assertEqual(self.status(1, "CLOSED").status_code, 404)
        self.client.app.dependency_overrides[get_current_user] = lambda: self.owner
        self.assertEqual(self.status(1, "CLOSED").status_code, 200)
        self.client.app.dependency_overrides[get_current_user] = lambda: self.other
        saved = self.client.get("/posts/saved").json()
        self.assertEqual(saved[0]["status"], "CLOSED")
        self.assertEqual(self.client.get(path).status_code, 200)
        self.client.app.dependency_overrides[get_current_user] = lambda: self.owner
        self.assertEqual(self.client.put(path + "/visibility", json={"is_private": True}).status_code, 200)
        self.assertEqual(self.client.get(path).json()["status"], "CLOSED")
        self.client.app.dependency_overrides[get_current_user] = lambda: self.other
        self.assertEqual(self.client.get("/posts/saved").json(), [])
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.post(path + "/comments", json={"content": "Hello"}).status_code, 404)
        self.client.app.dependency_overrides[get_current_user] = lambda: self.owner
        reopened = self.status(1, "ACTIVE")
        self.assertEqual(reopened.status_code, 200)
        self.assertTrue(reopened.json()["is_private"])
        self.client.put(path + "/visibility", json={"is_private": False})
        self.client.app.dependency_overrides[get_current_user] = lambda: self.other
        self.assertEqual(len(self.client.get("/posts/saved").json()), 1)
        self.client.app.dependency_overrides[get_current_user] = lambda: self.owner
        self.assertEqual(self.client.delete(path).status_code, 200)
        self.client.app.dependency_overrides[get_current_user] = lambda: self.other
        self.assertEqual(self.client.get("/posts/saved").json(), [])
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_comments_preserved_but_new_comments_require_active_post(self):
        self.seed(1, post_type=PostType.OFFER)
        path = f"/posts/{UUID(int=1)}"
        comment = self.client.post(path + "/comments", json={"content": "Still available?"})
        self.assertEqual(comment.status_code, 201)
        self.assertEqual(self.status(1, "CLOSED").status_code, 200)
        self.assertEqual(self.client.post(path + "/comments", json={"content": "Hello"}).status_code, 409)
        self.assertEqual(self.client.get(path + "/comments").json()[0]["id"], comment.json()["id"])
        self.assertEqual(self.client.get(path).json()["comment_count"], 1)
        self.status(1, "ACTIVE")
        self.assertEqual(self.client.post(path + "/comments", json={"content": "Hello"}).status_code, 201)

    def test_discussions_invalid_status_and_closed_post_editing(self):
        self.seed(1)
        self.assertEqual(self.status(1, "CLOSED").status_code, 409)
        self.assertEqual(self.status(1, "ACTIVE").status_code, 409)
        self.assertEqual(self.status(1, "RESOLVED").status_code, 422)
        self.assertEqual(self.status(999, "CLOSED").status_code, 404)
        self.seed(2, post_type=PostType.OFFER, created_at=datetime.now(timezone.utc).replace(tzinfo=None))
        self.status(2, "CLOSED")
        with Session(self.engine) as db:
            post = db.get(Post, UUID(int=2))
            location = PostLocationFields.model_validate(post, from_attributes=True)
        payload = {
            "title": "Changed", "description": "Still closed", "category": "PARKING",
            "post_type": "REQUEST", "location_id": "test",
        }
        with patch("app.api.posts.resolve_post_location", return_value=location):
            response = self.client.put(f"/posts/{UUID(int=2)}", json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["status"], "CLOSED")
            response = self.client.put(f"/posts/{UUID(int=2)}", json={**payload, "post_type": "DISCUSSION"})
            self.assertEqual(response.status_code, 409)
        with Session(self.engine) as db:
            self.assertEqual(db.get(Post, UUID(int=2)).status, PostStatus.CLOSED)
