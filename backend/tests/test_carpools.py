import unittest
from datetime import datetime, timedelta, timezone
from math import degrees
from unittest.mock import patch
from zoneinfo import ZoneInfo

import h3
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.carpools import router
from app.api.notifications import router as notifications_router
from app.api.rides import router as rides_router
from app.core.security import create_access_token
from app.db.base import Base
from app.db.dependencies import get_db
from app.models.carpool import CarpoolTrip
from app.models.user import User
import app.models.saved_post
from test_rides import place


class CarpoolAPITests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(self.engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            for user_id in range(1, 5):
                db.add(User(id=user_id, name=f"Member {user_id}", email=f"member{user_id}@example.test", provider="test", provider_id=str(user_id)))
            db.commit()
        app = FastAPI()
        app.include_router(router, prefix="/rides/carpools")
        app.include_router(rides_router, prefix="/rides")
        app.include_router(notifications_router, prefix="/notifications")

        def test_db():
            with Session(self.engine, autoflush=False) as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app)
        self.start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
        self.location_patch = patch("app.services.carpools.resolve_post_location", side_effect=place)
        self.location_patch.start()
        self.assertEqual(self.client.put("/rides/driver-profile", headers=self.headers(1), json={
            "vehicle": "Toyota Camry", "passenger_capacity": 3,
            "phone": "+14155550101", "eligibility_acknowledged": True,
        }).status_code, 200)

    def tearDown(self):
        self.location_patch.stop()
        self.client.close()
        self.engine.dispose()

    def headers(self, user_id=2):
        return {"Authorization": f"Bearer {create_access_token(user_id)}"}

    def leg(self, **updates):
        value = {
            "pickup_location_id": "pickup", "dropoff_location_id": "dropoff",
            "pickup_start": self.start.isoformat(), "pickup_end": (self.start + timedelta(minutes=30)).isoformat(),
            "timezone": "America/Los_Angeles", "seats": 3, "bags_per_person": 1,
            "amount": "40.00", "currency": "USD", "notes": "Meet at the public station.",
        }
        value.update(updates)
        return value

    def create(self, returning=False, **updates):
        payload = {"outbound": self.leg(**updates), "public_meeting_point_consent": True}
        if returning:
            payload["return_trip"] = self.leg(
                pickup_location_id="dropoff", dropoff_location_id="pickup",
                pickup_start=(self.start + timedelta(days=1)).isoformat(),
                pickup_end=(self.start + timedelta(days=1, minutes=30)).isoformat(), seats=1,
            )
        response = self.client.post("/rides/carpools/trips", headers=self.headers(1), json=payload)
        return response

    def request(self, trip_id, user_id=2, **updates):
        data = {"passengers": 1, "bags": 1, "message": "One small suitcase.", "rider_phone": "+14155550102"}
        data.update(updates)
        return self.client.post(f"/rides/carpools/trips/{trip_id}/requests", headers=self.headers(user_id), json=data)

    def detail(self, trip_id, user_id=2):
        return self.client.get(f"/rides/carpools/trips/{trip_id}", headers=self.headers(user_id))

    def act(self, trip_id, request_id, action, user_id=1):
        return self.client.post(
            f"/rides/carpools/trips/{trip_id}/requests/{request_id}/{action}",
            headers=self.headers(user_id), json={"reason": "Plans changed."} if action == "cancel" else None,
        )

    def test_auth_and_driver_required(self):
        self.assertEqual(self.client.get("/rides/carpools/trips").status_code, 401)
        self.assertEqual(self.client.get("/rides/carpools/mine").status_code, 401)
        self.assertEqual(self.client.get("/notifications").status_code, 401)
        self.assertEqual(self.client.post("/rides/carpools/trips", headers=self.headers(2), json={
            "outbound": self.leg(), "public_meeting_point_consent": True,
        }).status_code, 403)

    def test_map_search_bounds_and_area_limit(self):
        trip_id = self.create().json()["trip"]["id"]
        pickup = place("pickup")
        bounds = {
            "south": pickup.latitude - 0.01, "north": pickup.latitude + 0.01,
            "west": pickup.longitude - 0.01, "east": pickup.longitude + 0.01,
        }
        path = "/rides/carpools/trips/search"
        self.assertEqual(self.client.post(path, json={"bounds": bounds}).status_code, 401)
        response = self.client.post(path, headers=self.headers(), json={"bounds": bounds})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([trip["id"] for trip in response.json()["trips"]], [trip_id])
        self.assertFalse(response.json()["has_more"])
        empty = {"south": 0, "north": 0.01, "west": 0, "east": 0.01}
        self.assertEqual(self.client.post(path, headers=self.headers(), json={"bounds": empty}).json()["trips"], [])
        oversized = {"south": -60, "north": 60, "west": -120, "east": 120}
        self.assertEqual(self.client.post(path, headers=self.headers(), json={"bounds": oversized}).status_code, 422)

    def map_search(self, **updates):
        data = {"bounds": {"north": 37.56, "south": 37.54, "west": -121.99, "east": -121.97}}
        data.update(updates)
        return self.client.post("/rides/carpools/trips/search", headers=self.headers(), json=data)

    def test_map_search_exact_edges_and_h3_candidates(self):
        trip_id = self.create().json()["trip"]["id"]
        tiny = {"north": 37.5501, "south": 37.5499, "west": -121.9801, "east": -121.9799}
        self.assertEqual(len(self.map_search(bounds=tiny).json()["trips"]), 1)
        with Session(self.engine) as db:
            trip = db.get(CarpoolTrip, trip_id)
            trip.pickup = {**trip.pickup, "latitude": 37.551, "h3_cell_id": h3.latlng_to_cell(37.551, -121.98, 8)}
            db.commit()
        self.assertEqual(self.map_search(bounds=tiny).json()["trips"], [])
        edge = {"north": 37.551, "south": 37.55, "west": -121.98, "east": -121.97}
        self.assertEqual(len(self.map_search(bounds=edge).json()["trips"]), 1)
        with Session(self.engine) as db:
            trip = db.get(CarpoolTrip, trip_id)
            trip.pickup = {**trip.pickup, "h3_cell_id": place("far").h3_cell_id}
            db.commit()
        self.assertEqual(self.map_search(bounds=edge).json()["trips"], [])

    def test_map_search_antimeridian(self):
        trip_ids = [self.create().json()["trip"]["id"] for _ in range(3)]
        with Session(self.engine) as db:
            for trip_id, longitude in zip(trip_ids, (179.9, -179.9, 0)):
                trip = db.get(CarpoolTrip, trip_id)
                trip.pickup = {**trip.pickup, "latitude": 0.0, "longitude": longitude,
                               "h3_cell_id": h3.latlng_to_cell(0, longitude, 8)}
            db.commit()
        response = self.map_search(bounds={"north": 0.05, "south": -0.05, "west": 179.8, "east": -179.8})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([trip["id"] for trip in response.json()["trips"]], trip_ids[:2])

    def test_map_search_filters_before_pagination(self):
        reserved = self.create(seats=3).json()["trip"]["id"]
        request_id = self.request(reserved, passengers=2).json()["requests"][0]["id"]
        self.assertEqual(self.act(reserved, request_id, "accept").status_code, 200)
        self.create(dropoff_location_id="far")
        self.create(pickup_start=(self.start + timedelta(days=1)).isoformat(),
                    pickup_end=(self.start + timedelta(days=1, minutes=30)).isoformat())
        matching = [self.create().json()["trip"]["id"] for _ in range(2)]
        filters = {"departure_date": self.start.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat(),
                   "passengers": 2, "dropoff_location_id": "dropoff", "radius_km": 10, "limit": 1}
        first = self.map_search(**filters)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual([trip["id"] for trip in first.json()["trips"]], matching[:1])
        self.assertTrue(first.json()["has_more"])
        second = self.map_search(**filters, offset=1).json()
        self.assertEqual([trip["id"] for trip in second["trips"]], matching[1:])
        self.assertFalse(second["has_more"])
        self.assertEqual(self.map_search(**filters, pickup_location_id="far").json()["trips"], [])
        own = self.client.post("/rides/carpools/trips/search", headers=self.headers(1), json={
            "bounds": {"north": 37.56, "south": 37.54, "west": -121.99, "east": -121.97},
        })
        self.assertEqual(own.json()["trips"], [])

    def test_map_search_mile_radius_conversion(self):
        trip_ids = [self.create().json()["trip"]["id"] for _ in range(2)]
        destination = place("dropoff")
        with Session(self.engine) as db:
            for trip_id, miles in zip(trip_ids, (24.99, 25.01)):
                trip = db.get(CarpoolTrip, trip_id)
                trip.dropoff = {**trip.dropoff, "latitude": destination.latitude + degrees(miles * 1.609344 / 6371)}
            db.commit()
        response = self.map_search(dropoff_location_id="dropoff", radius_km=25 * 1.609344)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([trip["id"] for trip in response.json()["trips"]], trip_ids[:1])
        self.assertEqual(self.map_search(radius_km=50 * 1.609344).status_code, 200)

    def test_map_search_input_validation(self):
        for update in ({"bounds": None}, {"limit": 51}, {"offset": -1}, {"passengers": 0},
                       {"radius_km": 101}, {"departure_date": "invalid"},
                       {"bounds": {"north": 0, "south": 1, "west": 0, "east": 1}}):
            self.assertEqual(self.map_search(**update).status_code, 422)

    def test_linked_return_is_independent_and_private(self):
        created = self.create(returning=True)
        self.assertEqual(created.status_code, 201, created.text)
        data = created.json()
        outbound, returning = data["trip"]["id"], data["linked_trip"]["id"]
        self.assertEqual(data["linked_trip"]["available_seats"], 1)
        self.assertEqual(self.detail(returning).json()["linked_trip"]["id"], outbound)
        self.assertEqual(self.request(outbound, include_return=True).status_code, 201)
        driver = self.detail(outbound, 1).json()
        request = driver["requests"][0]
        self.assertIsNone(request["rider_phone"])
        self.assertIsNone(request["driver_phone"])
        self.assertEqual(driver["trip"]["available_seats"], 3)
        accepted = self.act(outbound, request["id"], "accept")
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["trip"]["available_seats"], 2)
        self.assertEqual(self.detail(outbound).json()["requests"][0]["driver_phone"], "+14155550101")
        self.assertEqual(self.detail(outbound, 3).json()["requests"], [])
        self.assertEqual(self.detail(returning).json()["requests"][0]["status"], "PENDING")
        self.assertEqual(self.detail(returning).json()["trip"]["available_seats"], 1)
        cancelled = self.act(outbound, request["id"], "cancel", 2)
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["trip"]["available_seats"], 3)
        self.assertIsNone(cancelled.json()["requests"][0]["driver_phone"])
        self.assertEqual(self.detail(returning).json()["requests"][0]["status"], "PENDING")

    def test_approval_capacity_permissions_and_idempotency(self):
        trip_id = self.create(seats=2).json()["trip"]["id"]
        first = self.request(trip_id, passengers=2).json()["requests"][0]["id"]
        second = self.request(trip_id, user_id=3).json()["requests"][0]["id"]
        self.assertEqual(self.act(trip_id, first, "accept", 2).status_code, 403)
        self.assertEqual(self.act(trip_id, first, "accept", 4).status_code, 404)
        self.assertEqual(self.act(trip_id, first, "cancel", 3).status_code, 404)
        self.assertEqual(self.act(trip_id, first, "accept").status_code, 200)
        self.assertEqual(self.act(trip_id, first, "accept").status_code, 200)
        self.assertEqual(self.act(trip_id, second, "accept").status_code, 409)
        self.assertEqual(self.act(trip_id, second, "decline").status_code, 200)
        self.assertEqual(self.act(trip_id, second, "accept").status_code, 409)
        self.assertEqual(self.detail(trip_id).json()["trip"]["status"], "FULL")
        self.assertEqual(self.act(trip_id, first, "cancel", 2).status_code, 200)
        self.assertEqual(self.detail(trip_id).json()["trip"]["available_seats"], 2)

    def test_invalid_inputs_and_duplicate_requests(self):
        for update in (
            {"seats": 4}, {"seats": 0}, {"amount": "-1"}, {"amount": "1.001"},
            {"timezone": "Bad/Zone"}, {"pickup_start": "2020-01-01T00:00:00Z"},
            {"pickup_start": self.start.replace(tzinfo=None).isoformat()},
            {"pickup_end": (self.start + timedelta(hours=3)).isoformat()},
            {"pickup_location_id": "dropoff"},
        ):
            response = self.create(**update)
            self.assertEqual(response.status_code, 422, response.text)
        trip_id = self.create().json()["trip"]["id"]
        for update in ({"bags": 2}, {"passengers": 4}, {"rider_phone": "invalid"}, {"include_return": True}):
            self.assertIn(self.request(trip_id, **update).status_code, (409, 422))
        self.assertEqual(self.request(trip_id, user_id=1).status_code, 403)
        self.assertEqual(self.request(trip_id).status_code, 201)
        self.assertEqual(self.request(trip_id).status_code, 409)
        self.assertEqual(self.detail(9999).status_code, 404)

    def test_atomic_both_direction_request_and_creation(self):
        trip = self.create(returning=True).json()["trip"]
        self.assertEqual(self.request(trip["id"], passengers=2, include_return=True).status_code, 409)
        self.assertEqual(self.detail(trip["id"]).json()["requests"], [])
        self.assertEqual(self.detail(trip["linked_trip_id"]).json()["requests"], [])
        with patch("app.services.carpools.resolve_post_location", side_effect=HTTPException(502, "Provider failed")):
            self.assertEqual(self.create().status_code, 502)
        with Session(self.engine) as db:
            self.assertEqual(len(list(db.scalars(select(CarpoolTrip)))), 2)

    def test_return_validation_consent_and_provider_failure_are_atomic(self):
        payload = {"outbound": self.leg(), "return_trip": self.leg(), "public_meeting_point_consent": True}
        self.assertEqual(self.client.post("/rides/carpools/trips", headers=self.headers(1), json=payload).status_code, 422)
        payload["return_trip"] = None
        payload["public_meeting_point_consent"] = False
        self.assertEqual(self.client.post("/rides/carpools/trips", headers=self.headers(1), json=payload).status_code, 422)
        values = [place("pickup"), place("dropoff"), HTTPException(502, "Return lookup failed")]
        with patch("app.services.carpools.resolve_post_location", side_effect=values):
            self.assertEqual(self.create(returning=True).status_code, 502)
        with Session(self.engine) as db:
            self.assertEqual(list(db.scalars(select(CarpoolTrip))), [])

    def test_trip_cancel_notifies_all_and_preserves_return(self):
        data = self.create(returning=True).json()
        trip_id, return_id = data["trip"]["id"], data["linked_trip"]["id"]
        request_id = self.request(trip_id, include_return=True).json()["requests"][0]["id"]
        self.act(trip_id, request_id, "accept")
        self.request(trip_id, user_id=3)
        path = f"/rides/carpools/trips/{trip_id}/cancel"
        self.assertEqual(self.client.post(path, headers=self.headers(2), json={"reason": "No"}).status_code, 403)
        response = self.client.post(path, headers=self.headers(1), json={"reason": "Car unavailable."})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["trip"]["status"], "CANCELLED")
        self.assertTrue(all(row["status"] == "CANCELLED" for row in response.json()["requests"]))
        self.assertEqual(self.detail(return_id).json()["requests"][0]["status"], "PENDING")
        self.assertEqual(self.request(trip_id, user_id=4).status_code, 409)
        before = self.client.get("/notifications", headers=self.headers(2)).json()["unread_count"]
        self.client.post(path, headers=self.headers(1), json={"reason": "Again"})
        inbox = self.client.get("/notifications", headers=self.headers(2)).json()
        self.assertEqual(inbox["unread_count"], before)
        notification_id = inbox["notifications"][0]["id"]
        self.assertEqual(self.client.post(f"/notifications/{notification_id}/read", headers=self.headers(3)).status_code, 404)
        self.assertEqual(self.client.post(f"/notifications/{notification_id}/read", headers=self.headers(2)).status_code, 200)
        self.assertEqual(self.client.get("/notifications", headers=self.headers(2)).json()["unread_count"], before - 1)

    def test_search_filters_pagination_and_my_trips(self):
        first = self.create().json()["trip"]
        self.create()
        route = "/rides/carpools/trips"
        self.assertEqual(self.client.get(route, headers=self.headers(1)).json()["trips"], [])
        page = self.client.get(route + "?limit=1", headers=self.headers()).json()
        self.assertTrue(page["has_more"])
        self.assertEqual(page["trips"][0]["id"], first["id"])
        next_page = self.client.get(route + "?limit=1&offset=1", headers=self.headers()).json()
        self.assertFalse(next_page["has_more"])
        self.assertNotEqual(next_page["trips"][0]["id"], first["id"])
        self.assertEqual(self.client.get(route + "?pickup_location_id=far", headers=self.headers()).json()["trips"], [])
        self.assertEqual(self.client.get(route + "?dropoff_location_id=far", headers=self.headers()).json()["trips"], [])
        self.assertEqual(self.client.get(route + "?passengers=4", headers=self.headers()).json()["trips"], [])
        self.request(first["id"])
        mine = self.client.get("/rides/carpools/mine", headers=self.headers()).json()
        self.assertEqual([row["id"] for row in mine["trips"]], [first["id"]])
        self.assertEqual(mine["trips"][0]["my_request_status"], "PENDING")

    def test_expired_departure_and_phone_snapshot(self):
        trip_id = self.create().json()["trip"]["id"]
        request_id = self.request(trip_id).json()["requests"][0]["id"]
        self.act(trip_id, request_id, "accept")
        self.client.put("/rides/driver-profile", headers=self.headers(1), json={
            "vehicle": "New car", "passenger_capacity": 1,
            "phone": "+14155550999", "eligibility_acknowledged": True,
        })
        self.assertEqual(self.detail(trip_id).json()["requests"][0]["driver_phone"], "+14155550101")
        self.assertEqual(self.detail(trip_id).json()["trip"]["vehicle"], "Toyota Camry")
        self.request(trip_id, user_id=3)
        with Session(self.engine) as db:
            trip = db.get(CarpoolTrip, trip_id)
            trip.pickup_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=31)
            trip.pickup_end = trip.pickup_start + timedelta(minutes=30)
            db.commit()
        self.assertEqual(self.detail(trip_id, 3).json()["requests"][0]["status"], "EXPIRED")
        self.assertEqual(self.detail(trip_id).json()["trip"]["status"], "DEPARTED")
        self.assertEqual(self.act(trip_id, request_id, "cancel", 2).status_code, 409)
        self.assertEqual(self.request(trip_id, user_id=4).status_code, 409)
        self.assertEqual(self.client.get("/rides/carpools/trips", headers=self.headers()).json()["trips"], [])

    def test_last_minute_cancellations_until_departure_window_ends(self):
        data = self.create(returning=True).json()
        trip_id, return_id = data["trip"]["id"], data["linked_trip"]["id"]
        first = self.request(trip_id, include_return=True).json()["requests"][0]["id"]
        second = self.request(trip_id, user_id=3).json()["requests"][0]["id"]
        self.assertEqual(self.act(trip_id, first, "accept").status_code, 200)
        during_window = self.start.replace(tzinfo=None) + timedelta(minutes=10)
        with patch("app.services.carpools.utc_now_naive", return_value=during_window):
            trip = self.detail(trip_id).json()["trip"]
            self.assertEqual(trip["status"], "DEPARTED")
            self.assertTrue(trip["can_cancel"])
            self.assertEqual(self.request(trip_id, user_id=4).status_code, 409)
            self.assertEqual(self.act(trip_id, second, "accept").status_code, 409)
            self.assertEqual(self.act(trip_id, first, "cancel", 2).status_code, 200)
            response = self.client.post(f"/rides/carpools/trips/{trip_id}/cancel", headers=self.headers(1), json={"reason": "Car trouble."})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["trip"]["status"], "CANCELLED")
            self.assertFalse(response.json()["trip"]["can_cancel"])
            self.assertEqual(self.detail(return_id).json()["trip"]["status"], "OPEN")
        other_id = self.create().json()["trip"]["id"]
        at_end = self.start.replace(tzinfo=None) + timedelta(minutes=30)
        with patch("app.services.carpools.utc_now_naive", return_value=at_end):
            self.assertFalse(self.detail(other_id).json()["trip"]["can_cancel"])
            response = self.client.post(f"/rides/carpools/trips/{other_id}/cancel", headers=self.headers(1), json={"reason": "Too late."})
            self.assertEqual(response.status_code, 409)

    def test_search_date_uses_saved_timezone_and_full_trips_are_hidden(self):
        start = self.start.replace(hour=1, minute=0)
        trip_id = self.create(
            seats=1, pickup_start=start.isoformat(), pickup_end=(start + timedelta(minutes=30)).isoformat(),
        ).json()["trip"]["id"]
        utc_date = start.date()
        local_date = utc_date - timedelta(days=1)
        path = "/rides/carpools/trips?departure_date="
        self.assertEqual(len(self.client.get(path + str(local_date), headers=self.headers()).json()["trips"]), 1)
        self.assertEqual(self.client.get(path + str(utc_date), headers=self.headers()).json()["trips"], [])
        request_id = self.request(trip_id).json()["requests"][0]["id"]
        self.act(trip_id, request_id, "accept")
        self.assertEqual(self.client.get(path + str(local_date), headers=self.headers(3)).json()["trips"], [])
        self.act(trip_id, request_id, "cancel", 2)
        self.assertEqual(len(self.client.get(path + str(local_date), headers=self.headers(3)).json()["trips"]), 1)


if __name__ == "__main__":
    unittest.main()
