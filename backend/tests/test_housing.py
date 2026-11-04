import unittest
from datetime import timedelta
from uuid import UUID, uuid4
from unittest.mock import patch

import h3
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.api.housing import router
from app.api.notifications import router as notifications_router
from app.core.ride_time import utc_now_naive
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app as production_app
from app.models.housing import HousingInquiry, HousingMessage, HousingPost, HousingReport, HousingSave
from app.models.notification import Notification
from app.models.user import User
from app.schemas.post import PostLocationFields


class HousingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.users = []
        with Session(self.engine, expire_on_commit=False) as db:
            for name in ("Owner", "Seeker", "Stranger"):
                user = User(id=uuid4(), name=name, email=f"{name}@example.test", provider="test", provider_id=name)
                db.add(user)
                self.users.append(user)
            db.commit()
        self.user = self.users[0]
        self.app = FastAPI()
        self.app.include_router(router, prefix="/housing")
        self.app.include_router(notifications_router, prefix="/notifications")

        def test_db():
            with Session(self.engine) as db:
                yield db
        self.app.dependency_overrides[get_db] = test_db
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.start = (utc_now_naive().date() + timedelta(days=3)).isoformat()
        self.end = (utc_now_naive().date() + timedelta(days=90)).isoformat()
        self.location = PostLocationFields(
            location_id="test-fremont", location="123 Test Street, Fremont, CA, USA",
            city="Fremont", country_code="US", state="CA", postal_code="94538",
            latitude=37.55, longitude=-121.98, h3_cell_id=h3.latlng_to_cell(37.55, -121.98, 8),
        )
        patcher = patch("app.api.housing.resolve_post_location", return_value=self.location)
        self.location_resolver = patcher.start()
        self.addCleanup(patcher.stop)

    def payload(self, **changes):
        return {
            "title": "Sunny private room", "description": "A furnished room near transit.",
            "kind": "LISTING", "room_type": "PRIVATE", "arrangement": "HOUSEHOLD",
            "stay_type": "LONG_TERM", "location_id": "test-fremont", "area": "Central Fremont",
            "amount": "950.00", "currency": "USD", "price_period": "MONTH",
            "available_from": self.start, "available_until": None, **changes,
        }

    def create(self, **changes):
        response = self.client.post("/housing", json=self.payload(**changes))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def search(self, **filters):
        response = self.client.post("/housing/search", json=filters)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_authentication_and_production_registration(self):
        self.assertIn("/housing/search", production_app.openapi()["paths"])
        self.app.dependency_overrides.pop(get_current_user)
        for path in ("/housing/me", "/housing/saved", "/housing/inquiries", f"/housing/{uuid4()}"):
            self.assertIn(self.client.get(path).status_code, (401, 403))
        self.assertIn(self.client.post("/housing/search", json={}).status_code, (401, 403))
        self.assertIn(self.client.post("/housing", json=self.payload()).status_code, (401, 403))

    def test_create_defaults_and_private_fields(self):
        item = self.create(title="  Sunny private room  ")
        self.assertEqual(item["title"], "Sunny private room")
        self.assertEqual(item["status"], "ACTIVE")
        self.assertFalse(item["my_saved"])
        self.assertEqual(set(item["owner"]), {"id", "name", "picture"})
        self.assertNotIn("email", str(item))
        self.assertEqual(item["latitude"], self.location.latitude)
        self.assertEqual(item["location"], self.location.location)
        self.assertEqual(item["minimum_stay_days"], 30)
        self.assertEqual(self.client.get(f"/housing/{item['id']}").status_code, 200)

    def test_optional_layout_counts_and_minimum_filters(self):
        studio = self.create(title="Transit studio home", bedroom_count=0, bathroom_count="1.0")
        larger = self.create(title="Two-bedroom home", bedroom_count=2, bathroom_count="1.5")
        older_style = self.create(title="Unspecified layout home")
        self.assertEqual(studio["bedroom_count"], 0)
        self.assertEqual(studio["bathroom_count"], "1.0")
        self.assertIsNone(older_style["bedroom_count"])
        self.assertIsNone(older_style["bathroom_count"])
        self.assertEqual([item["id"] for item in self.search(min_bedrooms=2, min_bathrooms="1.5")["items"]], [larger["id"]])
        self.assertEqual({item["id"] for item in self.search(min_bedrooms=0, min_bathrooms="1")["items"]}, {studio["id"], larger["id"]})
        for field, value in (("bedroom_count", -1), ("bedroom_count", 21), ("bedroom_count", 1.5),
                             ("bathroom_count", "0"), ("bathroom_count", "20.5"), ("bathroom_count", "1.25"),
                             ("min_bedrooms", -1), ("min_bathrooms", "1.25")):
            with self.subTest(field=field, value=value):
                if field.startswith("min_"):
                    response = self.client.post("/housing/search", json={field: value})
                else:
                    response = self.client.post("/housing", json=self.payload(**{field: value}))
                self.assertEqual(response.status_code, 422, response.text)

    def test_optional_bedroom_and_bathroom_counts(self):
        studio = self.create(title="Studio near transit", bedroom_count=0, bathroom_count="1.0")
        larger = self.create(title="Two-bedroom home", bedroom_count=2, bathroom_count="1.5")
        self.assertEqual(studio["bedroom_count"], 0)
        self.assertEqual(studio["bathroom_count"], "1.0")
        self.assertEqual(larger["bedroom_count"], 2)
        self.assertEqual(larger["bathroom_count"], "1.5")
        self.assertIsNone(self.create().get("bedroom_count"))
        self.assertEqual([item["id"] for item in self.search(min_bedrooms=2, min_bathrooms="1.5")["items"]], [larger["id"]])
        self.assertEqual({item["id"] for item in self.search(min_bedrooms=0, min_bathrooms="1")["items"]}, {studio["id"], larger["id"]})
        for field, value in (("bedroom_count", -1), ("bedroom_count", 21), ("bedroom_count", 1.5),
                             ("bathroom_count", "0"), ("bathroom_count", "20.5"),
                             ("bathroom_count", "1.25"), ("min_bedrooms", -1),
                             ("min_bathrooms", "1.25")):
            with self.subTest(field=field, value=value):
                if field.startswith("min_"):
                    response = self.client.post("/housing/search", json={field: value})
                else:
                    response = self.client.post("/housing", json=self.payload(**{field: value}))
                self.assertEqual(response.status_code, 422, response.text)

    def test_schema_validation(self):
        for changes in (
            {"amount": "-1"}, {"amount": "1.001"}, {"amount": "NaN"},
            {"amount": "1000000"}, {"currency": "usd"}, {"country_code": "USA"},
            {"available_from": self.end, "available_until": self.start},
            {"available_until": self.start, "minimum_stay_days": 30},
            {"room_type": "ANY"}, {"arrangement": "ANY"},
            {"arrangement": "TAKEOVER"}, {"available_spaces": 0}, {"occupants": 51},
            {"minimum_stay_days": 0}, {"status": "FILLED"}, {"owner_id": str(self.users[1].id)},
            {"title": "    "}, {"gender": "FEMALE"}, {"photo_urls": ["http://example.com/image.jpg"]},
            {"photo_urls": ["https://localhost/photo"]}, {"photo_urls": ["https://127.0.0.1/photo"]},
            {"photo_urls": ["https://10.0.0.1/photo"]}, {"photo_urls": ["https://user:pass@example.com/photo"]},
            {"photo_urls": ["https://example.com/p"] * 9},
        ):
            with self.subTest(changes=changes):
                response = self.client.post("/housing", json=self.payload(**changes))
                self.assertEqual(response.status_code, 422, response.text)
        item = self.create(arrangement="TAKEOVER", approval="PENDING", photo_urls=["https://example.com/room.jpg"])
        self.assertEqual(item["approval"], "PENDING")

    def test_discovery_intents_and_request_discovery(self):
        private_room = self.create()
        entire = self.create(room_type="ENTIRE", arrangement="RENTAL")
        request = self.create(kind="REQUEST", room_type="ENTIRE", arrangement="ANY")
        shared_request = self.create(kind="REQUEST", room_type="SHARED")
        together = self.create(kind="TOGETHER", room_type="ANY", arrangement="ANY")
        self.assertEqual({item["id"] for item in self.search()["items"]}, {private_room["id"], entire["id"]})
        people_ids = {request["id"], shared_request["id"], together["id"]}
        self.assertEqual({item["id"] for item in self.search(view="PEOPLE")["items"]}, people_ids)
        self.assertEqual({item["id"] for item in self.search(view="ROOMMATES")["items"]}, people_ids)
        self.assertEqual({item["id"] for item in self.search(view="PEOPLE", kind="REQUEST")["items"]}, {request["id"], shared_request["id"]})
        self.assertEqual([item["id"] for item in self.search(view="PEOPLE", kind="TOGETHER")["items"]], [together["id"]])
        self.assertEqual([item["id"] for item in self.search(view="PEOPLE", room_type="ENTIRE")["items"]], [request["id"]])
        self.assertEqual({item["id"] for item in self.search(kind="LISTING")["items"]}, {private_room["id"], entire["id"]})
        for invalid in ({"kind": "REQUEST"}, {"kind": "TOGETHER"}, {"view": "PEOPLE", "kind": "LISTING"},
                        {"view": "ROOMMATES", "kind": "LISTING"}):
            self.assertEqual(self.client.post("/housing/search", json=invalid).status_code, 422)

    def test_people_scope_before_bounds_filters_and_pagination(self):
        first = self.create(kind="REQUEST", room_type="ENTIRE", kitchen="EGGS_ALLOWED")
        second = self.create(kind="TOGETHER", room_type="ANY", kitchen="EGGS_ALLOWED")
        self.create()
        self.create(kind="REQUEST", is_private=True)
        closed = self.create(kind="REQUEST")
        self.client.put(f"/housing/{closed['id']}/status", json={"status": "FILLED"})
        self.create(kind="REQUEST", kitchen="VEGETARIAN")
        filters = {
            "view": "PEOPLE", "kitchen": "EGGS_ALLOWED", "limit": 1,
            "bounds": {"north": 37.56, "south": 37.54, "west": -121.99, "east": -121.97},
        }
        page1, page2 = self.search(**filters), self.search(**filters, offset=1)
        self.assertEqual([item["id"] for item in page1["items"]], [second["id"]])
        self.assertTrue(page1["has_more"])
        self.assertEqual([item["id"] for item in page2["items"]], [first["id"]])
        self.assertFalse(page2["has_more"])

    def test_structured_filters_and_date_coverage(self):
        item = self.create(
            kitchen="EGGS_ALLOWED", parking=True, laundry=True, furnishing="FURNISHED", bathroom="PRIVATE",
            available_until=self.end, arrangement="SUBLET", approval="OBTAINED", stay_type="SHORT_TERM",
        )
        filters = {
            "city": "fremont", "query": "transit", "room_type": "PRIVATE", "kitchen": "EGGS_ALLOWED",
            "parking": True, "laundry": True, "furnishing": "FURNISHED", "bathroom": "PRIVATE",
            "arrangement": "SUBLET", "stay_type": "SHORT_TERM",
            "min_amount": "900", "max_amount": "1000", "currency": "USD", "price_period": "MONTH",
            "available_from": self.start, "available_until": self.end,
        }
        self.assertEqual([row["id"] for row in self.search(**filters)["items"]], [item["id"]])
        for key, value in (("city", "San Jose"), ("kitchen", "VEGETARIAN"), ("parking", False),
                           ("currency", "CAD"), ("price_period", "WEEK"), ("max_amount", "949"),
                           ("query", "%")):
            with self.subTest(key=key):
                self.assertEqual(self.search(**{**filters, key: value})["items"], [])
        self.assertEqual(self.search(available_from=self.end, available_until=self.end)["items"], [])
        later = (utc_now_naive().date() + timedelta(days=100)).isoformat()
        self.assertEqual(self.search(available_from=later)["items"], [])
        for invalid in ({"max_amount": 1000}, {"min_amount": 1000, "max_amount": 1, "currency": "USD", "price_period": "MONTH"},
                        {"available_from": self.end, "available_until": self.start}, {"limit": 51}, {"offset": -1}):
            self.assertEqual(self.client.post("/housing/search", json=invalid).status_code, 422)

    def test_filtering_before_stable_pagination(self):
        first = self.create()
        second = self.create()
        self.create(is_private=True)
        third = self.create()
        self.client.put(f"/housing/{third['id']}/status", json={"status": "FILLED"})
        page1 = self.search(limit=1)
        page2 = self.search(limit=1, offset=1)
        self.assertTrue(page1["has_more"])
        self.assertFalse(page2["has_more"])
        self.assertEqual(page1["items"][0]["id"], second["id"])
        self.assertEqual(page2["items"][0]["id"], first["id"])

    def test_lifecycle_expiration_and_renewal(self):
        item = self.create()
        path = f"/housing/{item['id']}"
        self.assertEqual(self.client.put(path + "/status", json={"status": "FILLED"}).status_code, 200)
        self.assertEqual(self.search()["items"], [])
        self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.post(path + "/renew").status_code, 409)
        self.assertEqual(self.client.put(path + "/status", json={"status": "ACTIVE"}).status_code, 200)
        with Session(self.engine) as db:
            post = db.get(HousingPost, UUID(item["id"]))
            post.expires_at = utc_now_naive() - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.search()["items"], [])
        self.assertEqual(len(self.client.get("/housing/me?status=ACTIVE&expired=true").json()["items"]), 1)
        self.assertEqual(self.client.get("/housing/me?status=ACTIVE&expired=false").json()["items"], [])
        self.assertEqual(self.client.post(path + "/renew").status_code, 200)
        self.assertEqual(len(self.search()["items"]), 1)
        self.client.put(path + "/status", json={"status": "ARCHIVED"})
        self.assertEqual(self.client.get("/housing/me?status=ARCHIVED&limit=1").json()["items"][0]["id"], item["id"])

    def test_past_end_date_discovery_and_renewal(self):
        item = self.create()
        path = f"/housing/{item['id']}"
        with Session(self.engine) as db:
            post = db.get(HousingPost, UUID(item["id"]))
            post.available_from = utc_now_naive().date() - timedelta(days=60)
            post.available_until = utc_now_naive().date() - timedelta(days=1)
            db.commit()
        self.assertEqual(self.search()["items"], [])
        self.assertEqual(self.client.post(path + "/renew").status_code, 409)
        self.assertEqual(self.client.put(path + "/status", json={"status": "ACTIVE"}).status_code, 409)
        self.assertEqual(len(self.client.get("/housing/me?status=ACTIVE&expired=true").json()["items"]), 1)

    def test_owner_mutations_and_edit_preserve_status(self):
        item = self.create()
        path = f"/housing/{item['id']}"
        self.client.put(path + "/status", json={"status": "FILLED"})
        changed = self.client.put(path, json=self.payload(title="Updated room description"))
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["status"], "FILLED")
        self.assertIsNotNone(changed.json()["updated_at"])
        self.assertEqual(changed.json()["expires_at"], item["expires_at"])
        self.user = self.users[1]
        for suffix, payload in (("", self.payload()), ("/status", {"status": "ACTIVE"}), ("/visibility", {"is_private": True})):
            self.assertEqual(self.client.put(path + suffix, json=payload).status_code, 404)
        self.assertEqual(self.client.post(path + "/renew").status_code, 404)
        self.assertEqual(self.client.delete(path).status_code, 404)

    def test_saving_closed_posts_and_privacy(self):
        item = self.create()
        path = f"/housing/{item['id']}"
        self.user = self.users[1]
        for _ in range(2):
            self.assertEqual(self.client.put(path + "/saved").json(), {"saved": True})
        self.assertTrue(self.client.get(path).json()["my_saved"])
        self.user = self.users[0]
        self.client.put(path + "/status", json={"status": "FILLED"})
        self.user = self.users[1]
        self.assertEqual(len(self.client.get("/housing/saved").json()["items"]), 1)
        self.user = self.users[0]
        self.client.put(path + "/visibility", json={"is_private": True})
        self.user = self.users[1]
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.put(path + "/saved").status_code, 404)
        self.assertEqual(self.client.get("/housing/saved").json()["items"], [])
        self.user = self.users[0]
        self.client.put(path + "/visibility", json={"is_private": False})
        self.user = self.users[1]
        for _ in range(2):
            self.assertEqual(self.client.delete(path + "/saved").json(), {"saved": False})

    def test_inquiry_authorization_reply_and_lifecycle(self):
        item = self.create()
        path = f"/housing/{item['id']}"
        self.assertEqual(self.client.post(path + "/inquiries", json={"message": "Hello"}).status_code, 409)
        self.user = self.users[1]
        inquiry = self.client.post(path + "/inquiries", json={"message": "Is it available?"})
        self.assertEqual(inquiry.status_code, 201, inquiry.text)
        thread = inquiry.json()
        self.assertEqual(len(thread["messages"]), 1)
        self.assertEqual(set(thread["sender"]), {"id", "name", "picture"})
        repeated = self.client.post(path + "/inquiries", json={"message": "My dates are flexible."}).json()
        self.assertEqual(thread["id"], repeated["id"])
        self.assertEqual(len(repeated["messages"]), 2)
        reply_path = f"/housing/inquiries/{thread['id']}/messages"
        self.user = self.users[2]
        self.assertEqual(self.client.get("/housing/inquiries").json()["items"], [])
        self.assertEqual(self.client.post(reply_path, json={"message": "Unauthorized"}).status_code, 404)
        self.user = self.users[0]
        self.assertEqual(len(self.client.get("/housing/inquiries").json()["items"]), 1)
        self.client.put(path + "/status", json={"status": "FILLED"})
        self.assertEqual(self.client.post(reply_path, json={"message": "Sorry, now filled."}).status_code, 200)
        self.user = self.users[2]
        self.assertEqual(self.client.post(path + "/inquiries", json={"message": "New request"}).status_code, 409)
        self.user = self.users[1]
        self.assertEqual(self.client.post(reply_path, json={"message": "Thanks!"}).status_code, 200)
        self.user = self.users[0]
        self.client.put(path + "/visibility", json={"is_private": True})
        self.user = self.users[1]
        self.assertEqual(self.client.get("/housing/inquiries").json()["items"], [])
        self.assertEqual(self.client.post(reply_path, json={"message": "Private access"}).status_code, 404)

    def test_inquiry_notifications_and_exact_conversation_links(self):
        item = self.create()
        path = f"/housing/{item['id']}/inquiries"
        self.assertEqual(self.client.post(path, json={"message": "Own post"}).status_code, 409)
        self.user = self.users[1]
        thread = self.client.post(path, json={"message": "Private first message"}).json()
        self.assertEqual(self.client.get("/notifications").json()["notifications"], [])
        self.assertEqual(self.client.post(path, json={"message": "Private follow-up"}).status_code, 201)
        self.user = self.users[0]
        inbox = self.client.get("/notifications").json()
        self.assertEqual(inbox["unread_count"], 2)
        self.assertEqual({row["event_type"] for row in inbox["notifications"]},
                         {"housing.inquiry_received", "housing.reply_received"})
        for row in inbox["notifications"]:
            self.assertEqual(row["category"], "housing")
            self.assertEqual(row["resource_id"], thread["id"])
            self.assertFalse(row["is_read"])
            self.assertNotIn("Private", row["message"])
            target = row["target_path"]
            self.assertEqual(target, f"/housing/inquiries?inquiry_id={thread['id']}")
            self.assertEqual(self.client.get(target + "&offset=100").json()["items"][0]["id"], thread["id"])
        reply_path = f"/housing/inquiries/{thread['id']}/messages"
        self.assertEqual(self.client.post(reply_path, json={"message": "Private owner reply"}).status_code, 200)
        self.assertEqual(self.client.get("/notifications").json()["unread_count"], 2)
        self.user = self.users[1]
        received = self.client.get("/notifications").json()
        self.assertEqual(received["unread_count"], 1)
        self.assertEqual(received["notifications"][0]["event_type"], "housing.reply_received")
        notification_id = received["notifications"][0]["id"]
        self.assertEqual(self.client.post(f"/notifications/{notification_id}/read").status_code, 200)
        self.assertEqual(self.client.get("/notifications/unread-count").json()["unread_count"], 0)
        self.assertEqual(self.client.post(reply_path, json={"message": "Seeker reply"}).status_code, 200)
        self.user = self.users[2]
        self.assertEqual(self.client.get(target).status_code, 404)
        self.assertEqual(self.client.post(reply_path, json={"message": "Unauthorized"}).status_code, 404)
        self.assertEqual(self.client.get("/notifications").json()["notifications"], [])
        self.assertEqual(self.client.get("/housing/inquiries?inquiry_id=invalid").status_code, 422)
        self.assertEqual(self.client.get(f"/housing/inquiries?inquiry_id={uuid4()}").status_code, 404)
        self.user = self.users[0]
        self.assertEqual(self.client.get("/notifications").json()["unread_count"], 3)
        self.client.put(f"/housing/{item['id']}/visibility", json={"is_private": True})
        self.user = self.users[1]
        self.assertEqual(self.client.get(target).status_code, 404)
        self.assertEqual(self.client.post(reply_path, json={"message": "Private access"}).status_code, 404)
        self.user = self.users[0]
        self.assertEqual(self.client.get(target).status_code, 200)
        self.assertEqual(self.client.delete(f"/housing/{item['id']}").status_code, 200)
        self.assertEqual(self.client.get(target).status_code, 404)

    def test_notification_link_finds_thread_beyond_first_page(self):
        threads = []
        for index in range(21):
            self.user = self.users[0]
            item = self.create(title=f"Room {index}")
            self.user = self.users[1]
            response = self.client.post(f"/housing/{item['id']}/inquiries", json={"message": "Interested"})
            self.assertEqual(response.status_code, 201, response.text)
            threads.append(response.json()["id"])
        self.user = self.users[0]
        first_page = self.client.get("/housing/inquiries").json()
        self.assertTrue(first_page["has_more"])
        self.assertNotIn(threads[0], [row["id"] for row in first_page["items"]])
        target = f"/housing/inquiries?inquiry_id={threads[0]}"
        result = self.client.get(target)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual([row["id"] for row in result.json()["items"]], [threads[0]])
        self.assertFalse(result.json()["has_more"])

    def test_notification_failure_rolls_back_message_and_inquiry(self):
        item = self.create()
        self.user = self.users[1]
        path = f"/housing/{item['id']}/inquiries"
        with patch("app.api.housing.notifications.notify", side_effect=RuntimeError("Notification write failed")):
            with self.assertRaisesRegex(RuntimeError, "Notification write failed"):
                self.client.post(path, json={"message": "Must not persist"})
        with Session(self.engine) as db:
            for model in (HousingInquiry, HousingMessage, Notification):
                self.assertEqual(list(db.scalars(select(model))), [])
        thread = self.client.post(path, json={"message": "Persisted"}).json()
        self.user = self.users[0]
        with patch("app.api.housing.notifications.notify", side_effect=RuntimeError("Notification write failed")):
            with self.assertRaisesRegex(RuntimeError, "Notification write failed"):
                self.client.post(f"/housing/inquiries/{thread['id']}/messages", json={"message": "Must not persist"})
        with Session(self.engine) as db:
            self.assertEqual(len(list(db.scalars(select(HousingMessage)))), 1)
            self.assertEqual(len(list(db.scalars(select(Notification)))), 1)

    def test_reports_and_delete_cascade(self):
        item = self.create()
        path = f"/housing/{item['id']}"
        report = {"reason": "INACCURATE", "details": "Price seems inaccurate"}
        self.assertEqual(self.client.post(path + "/reports", json=report).status_code, 409)
        self.user = self.users[1]
        self.assertEqual(self.client.post(path + "/reports", json=report).status_code, 201)
        self.assertEqual(self.client.post(path + "/reports", json=report).status_code, 409)
        self.client.put(path + "/saved")
        self.client.post(path + "/inquiries", json={"message": "Checking availability."})
        self.user = self.users[0]
        self.assertEqual(self.client.delete(path).status_code, 200)
        self.assertEqual(self.client.get(path).status_code, 404)
        with Session(self.engine) as db:
            for model in (HousingPost, HousingInquiry, HousingMessage, HousingSave, HousingReport):
                self.assertEqual(list(db.scalars(select(model))), [])

    def test_database_checks(self):
        item = self.create()
        with Session(self.engine) as db:
            post = db.get(HousingPost, UUID(item["id"]))
            post.room_type = "ANY"
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

    def test_server_resolves_location_and_edit_updates_h3(self):
        item = self.create()
        self.assertEqual(item["h3_cell_id"], h3.latlng_to_cell(37.55, -121.98, 8))
        for field in ("city", "country_code", "latitude", "longitude", "location", "h3_cell_id"):
            self.assertEqual(self.client.post("/housing", json=self.payload(**{field: "spoofed"})).status_code, 422)
        missing = self.payload()
        missing.pop("location_id")
        self.assertEqual(self.client.post("/housing", json=missing).status_code, 422)
        self.location_resolver.return_value = self.location.model_copy(update={
            "location_id": "new-place", "location": "San Jose, CA", "city": "San Jose",
            "latitude": 37.33, "longitude": -121.89, "h3_cell_id": h3.latlng_to_cell(37.33, -121.89, 8),
        })
        changed = self.client.put(f"/housing/{item['id']}", json=self.payload(location_id="new-place"))
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["city"], "San Jose")
        self.assertEqual(changed.json()["h3_cell_id"], h3.latlng_to_cell(37.33, -121.89, 8))
        self.location_resolver.reset_mock()
        self.assertEqual(self.client.put(f"/housing/{item['id']}", json=self.payload(location_id="new-place")).status_code, 200)
        self.location_resolver.assert_not_called()
        self.location_resolver.side_effect = HTTPException(502, "Location provider request failed")
        failed = self.client.post("/housing", json=self.payload())
        self.assertEqual(failed.status_code, 502)
        self.assertEqual(len(self.search()["items"]), 1)

    def test_bounds_h3_exact_edges_filters_and_pagination(self):
        first = self.create(kitchen="EGGS_ALLOWED")
        second = self.create(kitchen="VEGETARIAN")
        hidden = self.create(is_private=True)
        closed = self.create()
        self.client.put(f"/housing/{closed['id']}/status", json={"status": "FILLED"})
        outside = self.create()
        with Session(self.engine) as db:
            row = db.get(HousingPost, UUID(outside["id"]))
            # Same H3 candidate cell, but beyond the requested rectangle.
            row.latitude = 37.5502
            db.commit()
        bounds = {"north": 37.5501, "south": 37.5499, "west": -121.9801, "east": -121.9799}
        page1 = self.search(bounds=bounds, limit=1)
        page2 = self.search(bounds=bounds, limit=1, offset=1)
        self.assertEqual([row["id"] for row in page1["items"]], [second["id"]])
        self.assertEqual([row["id"] for row in page2["items"]], [first["id"]])
        self.assertTrue(page1["has_more"])
        self.assertFalse(page2["has_more"])
        matching = self.search(bounds=bounds, kitchen="EGGS_ALLOWED", max_amount=950, currency="USD", price_period="MONTH")
        self.assertEqual([row["id"] for row in matching["items"]], [first["id"]])
        self.assertNotIn(hidden["id"], str(matching))
        invalid_bounds = (
            {"north": 90, "south": -90, "west": -180, "east": 180},
            {**bounds, "north": bounds["south"]},
            {**bounds, "east": bounds["west"]},
            {**bounds, "north": 91},
        )
        for invalid in invalid_bounds:
            self.assertEqual(self.client.post("/housing/search", json={"bounds": invalid}).status_code, 422)

    def test_bounds_include_edges_and_exclude_every_outside_direction(self):
        bounds = {"north": 37.551, "south": 37.549, "west": -121.981, "east": -121.979}
        expected = set()
        positions = (
            (37.551, -121.98, True), (37.549, -121.98, True),
            (37.55, -121.981, True), (37.55, -121.979, True),
            (37.5511, -121.98, False), (37.5489, -121.98, False),
            (37.55, -121.9811, False), (37.55, -121.9789, False),
        )
        for latitude, longitude, included in positions:
            self.location_resolver.return_value = self.location.model_copy(update={
                "latitude": latitude, "longitude": longitude,
                "h3_cell_id": h3.latlng_to_cell(latitude, longitude, 8),
            })
            item = self.create()
            if included:
                expected.add(item["id"])
        self.assertEqual({row["id"] for row in self.search(bounds=bounds)["items"]}, expected)
        with patch("app.api.housing.h3_cells_for_bounds", return_value=[]):
            self.assertEqual(self.search(bounds=bounds)["items"], [])

    def test_antimeridian_and_coordinate_less_existing_posts(self):
        items = []
        for lng in (179.95, -179.95, 179.5):
            self.location_resolver.return_value = self.location.model_copy(update={
                "latitude": 0.0, "longitude": lng, "h3_cell_id": h3.latlng_to_cell(0.0, lng, 8),
            })
            items.append(self.create())
        bounds = {"north": 0.05, "south": -0.05, "west": 179.9, "east": -179.9}
        self.assertEqual({row["id"] for row in self.search(bounds=bounds)["items"]}, {items[0]["id"], items[1]["id"]})
        with Session(self.engine) as db:
            row = db.get(HousingPost, UUID(items[0]["id"]))
            for key in ("location_id", "location", "latitude", "longitude", "h3_cell_id", "state", "postal_code"):
                setattr(row, key, None)
            db.commit()
        self.assertEqual(len(self.search()["items"]), 3)
        self.assertEqual([row["id"] for row in self.search(bounds=bounds)["items"]], [items[1]["id"]])
        self.assertIsNone(self.client.get(f"/housing/{items[0]['id']}").json()["location_id"])


if __name__ == "__main__":
    unittest.main()
