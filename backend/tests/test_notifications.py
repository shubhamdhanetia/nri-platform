import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.api.carpools import router as carpools_router
from app.api.notifications import router
from app.db.notification_migration import migrate_carpool_notifications
from app.db.base import Base
from app.core.config import settings
from app.models.carpool import CarpoolNotification, CarpoolTrip
from app.models.notification import Notification
from app.models.ride import RideOffer
from app.models.user import User
from app.services.notifications import notify
import test_rides


class NotificationAPITests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_rides.RideAPITests()
        self.fixture.setUp()
        self.fixture.client.app.include_router(router, prefix="/notifications")
        self.fixture.client.app.include_router(carpools_router, prefix="/rides/carpools")
        self.client = self.fixture.client
        self.engine = self.fixture.engine
        self.location_patch = patch("app.services.carpools.resolve_post_location", side_effect=test_rides.place)
        self.location_patch.start()

    def tearDown(self):
        self.location_patch.stop()
        self.fixture.tearDown()

    def inbox(self, user_id=1, query=""):
        response = self.client.get("/notifications" + query, headers=self.fixture.headers(user_id))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def event_types(self, user_id=1):
        return [row["event_type"] for row in self.inbox(user_id)["notifications"]]

    def carpool(self):
        self.fixture.driver()
        leg = {
            "pickup_location_id": "pickup", "dropoff_location_id": "dropoff",
            "pickup_start": self.fixture.start.isoformat(), "pickup_end": self.fixture.end.isoformat(),
            "timezone": "UTC", "seats": 2, "bags_per_person": 1, "amount": "40.00", "currency": "USD",
        }
        response = self.client.post("/rides/carpools/trips", headers=self.fixture.headers(2), json={
            "outbound": leg, "public_meeting_point_consent": True,
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["trip"]["id"]

    def test_auth_private_reads_pagination_and_generic_feature(self):
        self.assertEqual(self.client.get("/notifications").status_code, 401)
        self.assertEqual(self.client.get("/notifications/unread-count").status_code, 401)
        self.assertEqual(self.client.post("/notifications/1/read").status_code, 401)
        with Session(self.engine) as db:
            for index in range(3):
                notify(db, user_id=1, category="future-feature", event_type="future.updated",
                       resource_id=index + 1, target_path="/profile", message=f"Update {index}")
            notify(db, user_id=2, category="ride", event_type="ride.test", resource_id=1,
                   target_path="/rides/1", message="Private update for another member")
            db.commit()
        first = self.inbox(query="?limit=2")
        self.assertEqual(first["unread_count"], 3)
        self.assertTrue(first["has_more"])
        self.assertEqual([row["message"] for row in first["notifications"]], ["Update 2", "Update 1"])
        self.assertTrue(first["notifications"][0]["created_at"].endswith("+00:00"))
        self.assertEqual(first["notifications"][0]["category"], "future-feature")
        self.assertNotIn("user_id", first["notifications"][0])
        last = self.inbox(query="?limit=2&offset=2")
        self.assertFalse(last["has_more"])
        self.assertEqual(last["notifications"][0]["message"], "Update 0")
        row_id = first["notifications"][0]["id"]
        path = f"/notifications/{row_id}/read"
        self.assertEqual(self.client.post(path, headers=self.fixture.headers(2)).status_code, 404)
        self.assertEqual(self.client.post(path, headers=self.fixture.headers(1)).status_code, 200)
        self.assertEqual(self.client.post(path, headers=self.fixture.headers(1)).status_code, 200)
        self.assertEqual(self.client.post("/notifications/99999/read", headers=self.fixture.headers(1)).status_code, 404)
        self.assertEqual(self.inbox()["unread_count"], 2)
        self.assertEqual(self.inbox(2)["unread_count"], 1)
        self.assertEqual(self.client.get("/notifications/unread-count", headers=self.fixture.headers()).json(), {"unread_count": 2})
        for query in ("?offset=-1", "?limit=0", "?limit=51"):
            self.assertEqual(self.client.get("/notifications" + query, headers=self.fixture.headers()).status_code, 422)

    def test_ride_offers_withdrawals_and_confirmations(self):
        ride_id, first = self.fixture.seed_offer()
        self.assertEqual(self.event_types(), ["ride.offer_received"])
        event = self.inbox()["notifications"][0]
        self.assertEqual(event["target_path"], f"/rides/{ride_id}")
        self.assertEqual(event["resource_id"], ride_id)
        self.assertNotIn("phone", str(event))
        self.assertEqual(self.event_types(2), [])
        self.assertEqual(self.event_types(3), [])
        self.fixture.driver(user_id=3)
        second = self.fixture.offer(ride_id, user_id=3).json()["offers"][0]["id"]
        self.assertEqual(self.fixture.confirm(ride_id, first).status_code, 200)
        self.assertEqual(self.event_types(2), ["ride.booking_confirmed"])
        self.assertEqual(self.event_types(3), ["ride.offer_not_selected"])
        self.assertEqual(self.fixture.confirm(ride_id, first).status_code, 200)
        self.assertEqual(self.event_types(2), ["ride.booking_confirmed"])
        self.assertEqual(self.fixture.confirm(ride_id, second).status_code, 409)
        self.assertEqual(self.event_types(3), ["ride.offer_not_selected"])
        self.assertEqual(self.event_types(4), [])

    def test_withdraw_resubmit_and_request_cancel_events(self):
        ride_id, offer_id = self.fixture.seed_offer()
        path = f"/rides/requests/{ride_id}/offers/{offer_id}/withdraw"
        self.assertEqual(self.client.post(path, headers=self.fixture.headers(2)).status_code, 200)
        self.assertEqual(self.client.post(path, headers=self.fixture.headers(2)).status_code, 200)
        self.assertEqual(self.event_types().count("ride.offer_withdrawn"), 1)
        self.assertEqual(self.fixture.offer(ride_id).status_code, 201)
        self.assertEqual(self.event_types().count("ride.offer_received"), 2)
        path = f"/rides/requests/{ride_id}/cancel"
        self.assertEqual(self.client.post(path, headers=self.fixture.headers()).status_code, 200)
        self.assertEqual(self.client.post(path, headers=self.fixture.headers()).status_code, 200)
        self.assertEqual(self.event_types(2), ["ride.request_cancelled"])

    def test_booking_cancellation_notifies_counterpart_only(self):
        for cancelled_by, recipient in ((1, 2), (2, 1)):
            ride_id, offer_id = self.fixture.seed_offer()
            self.fixture.confirm(ride_id, offer_id)
            before_actor = len(self.event_types(cancelled_by))
            before_recipient = self.event_types(recipient).count("ride.booking_cancelled")
            path = f"/rides/requests/{ride_id}/booking/cancel"
            for _ in range(2):
                response = self.client.post(path, headers=self.fixture.headers(cancelled_by), json={"reason": "Private reason."})
                self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(self.event_types(cancelled_by)), before_actor)
            self.assertEqual(self.event_types(recipient).count("ride.booking_cancelled"), before_recipient + 1)
            self.assertNotIn("Private reason", str(self.inbox(recipient)))

    def test_ride_completion_is_notified_once(self):
        ride_id, offer_id = self.fixture.seed_offer()
        self.fixture.confirm(ride_id, offer_id)
        path = f"/rides/requests/{ride_id}/booking/complete"
        self.assertEqual(self.client.post(path, headers=self.fixture.headers()).status_code, 409)
        self.assertNotIn("ride.booking_completed", self.event_types(2))
        with patch("app.services.rides.utc_now_naive", return_value=self.fixture.end.replace(tzinfo=None) + timedelta(minutes=1)):
            self.assertEqual(self.client.post(path, headers=self.fixture.headers()).status_code, 200)
            self.assertEqual(self.client.post(path, headers=self.fixture.headers()).status_code, 200)
        self.assertEqual(self.event_types(2).count("ride.booking_completed"), 1)

    def test_legacy_carpool_inbox_endpoints_are_removed(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertNotIn("/rides/carpools/inbox", paths)
        self.assertNotIn("/rides/carpools/inbox/{notification_id}/read", paths)
        self.assertIn("/notifications", paths)
        self.assertIn("/notifications/{notification_id}/read", paths)
        self.assertEqual(self.client.get("/rides/carpools/inbox", headers=self.fixture.headers()).status_code, 404)
        self.assertEqual(self.client.post("/rides/carpools/inbox/1/read", headers=self.fixture.headers()).status_code, 404)

    def test_carpool_and_ride_events_share_one_inbox(self):
        ride_id, _ = self.fixture.seed_offer()
        trip_id = self.carpool()
        response = self.client.post(f"/rides/carpools/trips/{trip_id}/requests", headers=self.fixture.headers(1), json={
            "passengers": 1, "bags": 0, "rider_phone": "+14155550101",
        })
        self.assertEqual(response.status_code, 201, response.text)
        request_id = response.json()["requests"][0]["id"]
        self.assertEqual(self.event_types(2), ["carpool.seat_requested"])
        self.assertEqual(self.client.post(f"/rides/carpools/trips/{trip_id}/requests/{request_id}/accept", headers=self.fixture.headers(2)).status_code, 200)
        inbox = self.inbox()
        self.assertEqual({row["category"] for row in inbox["notifications"]}, {"ride", "carpool"})
        carpool = next(row for row in inbox["notifications"] if row["category"] == "carpool")
        self.assertEqual(carpool["event_type"], "carpool.request_confirmed")
        self.assertEqual(carpool["target_path"], f"/rides/carpools/{trip_id}")
        self.assertEqual(self.client.post(f"/notifications/{carpool['id']}/read", headers=self.fixture.headers()).status_code, 200)
        self.assertEqual(self.inbox()["unread_count"], inbox["unread_count"] - 1)
        ride_event = next(row for row in inbox["notifications"] if row["category"] == "ride")
        self.assertEqual(ride_event["resource_id"], ride_id)
        self.assertEqual(self.client.post(f"/notifications/{ride_event['id']}/read", headers=self.fixture.headers()).status_code, 200)
        self.assertEqual(self.inbox()["unread_count"], 0)

    def test_carpool_decline_and_cancellation_events(self):
        for action in ("decline", "cancel", "trip-cancel"):
            trip_id = self.carpool()
            response = self.client.post(f"/rides/carpools/trips/{trip_id}/requests", headers=self.fixture.headers(1), json={
                "passengers": 1, "bags": 0, "rider_phone": "+14155550101",
            })
            self.assertEqual(response.status_code, 201, response.text)
            request_id = response.json()["requests"][0]["id"]
            base = f"/rides/carpools/trips/{trip_id}"
            if action == "cancel":
                self.assertEqual(self.client.post(f"{base}/requests/{request_id}/accept", headers=self.fixture.headers(2)).status_code, 200)
                response = self.client.post(f"{base}/requests/{request_id}/cancel", headers=self.fixture.headers(1), json={"reason": "Private reason."})
                self.assertEqual(response.status_code, 200)
                self.assertIn("carpool.request_cancelled", self.event_types(2))
            elif action == "decline":
                response = self.client.post(f"{base}/requests/{request_id}/decline", headers=self.fixture.headers(2))
                self.assertEqual(response.status_code, 200)
                self.assertIn("carpool.request_declined", self.event_types(1))
            else:
                response = self.client.post(f"{base}/cancel", headers=self.fixture.headers(2), json={"reason": "Private reason."})
                self.assertEqual(response.status_code, 200)
                self.assertIn("carpool.trip_cancelled", self.event_types(1))
        self.assertNotIn("Private reason", str(self.inbox(1)) + str(self.inbox(2)))

    def test_migration_preserves_history_and_never_resets_read_state(self):
        trip_id = self.carpool()
        with Session(self.engine) as db:
            first = CarpoolNotification(user_id=1, trip_id=trip_id, message="Historical unread", is_read=False)
            second = CarpoolNotification(user_id=1, trip_id=trip_id, message="Historical read", is_read=True)
            db.add_all([first, second])
            db.commit()
            created = first.created_at
        migrate_carpool_notifications(self.engine)
        rows = self.inbox()["notifications"]
        self.assertEqual({row["message"] for row in rows}, {"Historical unread", "Historical read"})
        unread = next(row for row in rows if not row["is_read"])
        self.assertEqual(unread["created_at"], created.isoformat() + "+00:00")
        self.assertEqual(unread["target_path"], f"/rides/carpools/{trip_id}")
        self.client.post(f"/notifications/{unread['id']}/read", headers=self.fixture.headers())
        migrate_carpool_notifications(self.engine)
        self.assertEqual(self.inbox()["unread_count"], 0)
        self.assertEqual(len(self.inbox()["notifications"]), 2)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(CarpoolNotification)), 2)

    def test_business_mutation_and_event_rollback_together(self):
        ride_id = self.fixture.create().json()["id"]
        self.fixture.driver()

        def fail_after_event(db, **kwargs):
            notify(db, **kwargs)
            raise HTTPException(503, "Notification transaction failed")

        with patch("app.services.rides.notifications.notify", side_effect=fail_after_event):
            self.assertEqual(self.fixture.offer(ride_id).status_code, 503)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(RideOffer)), 0)
            self.assertEqual(db.scalar(select(func.count()).select_from(Notification)), 0)

    def test_invalid_notification_target_rejected(self):
        with Session(self.engine) as db:
            for target in ("https://example.test", "//example.test", "/\\example.test"):
                with self.assertRaises(ValueError):
                    notify(db, user_id=1, category="test", event_type="test", resource_id=1,
                           target_path=target, message="Test")


@unittest.skipUnless(os.getenv("RIDE_TEST_POSTGRES") == "1", "Set RIDE_TEST_POSTGRES=1 for isolated PostgreSQL migration tests")
class NotificationPostgresTests(unittest.TestCase):
    def test_concurrent_startup_migration_is_idempotent(self):
        engine = create_engine(settings.DATABASE_URL)
        self.assertEqual(engine.dialect.name, "postgresql")
        schema = "notification_test_" + uuid4().hex
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        isolated = engine.execution_options(schema_translate_map={None: schema})
        try:
            Base.metadata.create_all(isolated)
            with Session(isolated) as db:
                db.add(User(id=1, name="Test member", email="notification@example.test", provider="test", provider_id="notification"))
                db.commit()
                start = datetime(2030, 11, 7, 16)
                trip = CarpoolTrip(
                    driver_id=1, pickup=test_rides.place("pickup").model_dump(),
                    dropoff=test_rides.place("dropoff").model_dump(), pickup_start=start,
                    pickup_end=start + timedelta(minutes=30), timezone="UTC", seats=1,
                    bags_per_person=1, amount=40, currency="USD", vehicle="Test car", notes="",
                )
                db.add(trip)
                db.flush()
                trip_id = trip.id
                db.add(CarpoolNotification(user_id=1, trip_id=trip_id, message="Historical event", is_read=False))
                notify(db, user_id=1, category="ride", event_type="ride.test", resource_id=1,
                       target_path="/rides/1", message="Existing shared event")
                db.commit()
            barrier = Barrier(2)

            def migrate():
                barrier.wait(timeout=10)
                migrate_carpool_notifications(isolated)

            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(migrate)
                second = executor.submit(migrate)
                first.result(timeout=20)
                second.result(timeout=20)
            with Session(isolated) as db:
                rows = list(db.scalars(select(Notification).order_by(Notification.id)))
                self.assertEqual(len(rows), 2)
                legacy = next(row for row in rows if row.legacy_carpool_id is not None)
                self.assertEqual(legacy.message, "Historical event")
                self.assertEqual(legacy.target_path, f"/rides/carpools/{trip_id}")
                legacy.is_read = True
                db.commit()
            migrate_carpool_notifications(isolated)
            with Session(isolated) as db:
                self.assertEqual(db.scalar(select(func.count()).select_from(Notification)), 2)
                self.assertTrue(db.scalar(select(Notification).where(Notification.legacy_carpool_id.is_not(None))).is_read)
        finally:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
            engine.dispose()
