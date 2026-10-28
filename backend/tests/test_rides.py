import unittest
import h3
from datetime import datetime, timedelta, timezone
from math import degrees
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.posts import router as posts_router
from app.api.rides import router
from app.core.security import create_access_token
from app.db.base import Base
from app.db.dependencies import get_db
from app.models.ride import DriverProfile, RideBooking, RideOffer, RideRequest
import app.models.saved_post
from app.models.user import User
from app.schemas.post import PostLocationFields


def place(location_id: str) -> PostLocationFields:
    coordinates = {"pickup": (37.55, -121.98), "dropoff": (37.62, -122.38), "far": (40.71, -74.0)}
    lat, lng = coordinates[location_id]
    return PostLocationFields(
        location_id=location_id, location=f"Exact address: {location_id}", city="Fremont",
        country_code="US", postal_code="94538", state="CA", latitude=lat, longitude=lng,
        h3_cell_id=h3.latlng_to_cell(lat, lng, 8),
    )


class RideAPITests(unittest.TestCase):
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
        app.include_router(router, prefix="/rides")
        app.include_router(posts_router, prefix="/posts")

        def test_db():
            with Session(self.engine, autoflush=False) as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app)
        self.start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
        self.end = self.start + timedelta(minutes=30)
        self.location_patch = patch("app.services.rides.resolve_post_location", side_effect=place)
        self.search_patch = patch("app.api.rides.resolve_post_location", side_effect=place)
        self.location_patch.start()
        self.search_patch.start()

    def tearDown(self):
        self.location_patch.stop()
        self.search_patch.stop()
        self.client.close()
        self.engine.dispose()

    def headers(self, user_id=1):
        return {"Authorization": f"Bearer {create_access_token(user_id)}"}

    def create(self, **updates):
        payload = {
            "pickup_location_id": "pickup", "dropoff_location_id": "dropoff",
            "pickup_start": self.start.isoformat(), "pickup_end": self.end.isoformat(),
            "timezone": "America/Los_Angeles", "passengers": 1, "bags": 2, "notes": "Two bags",
            "rider_phone": "+14155550101", "currency": "USD", "exact_location_consent": True,
        }
        payload.update(updates)
        return self.client.post("/rides/requests", json=payload, headers=self.headers())

    def driver(self, user_id=2, **updates):
        payload = {"vehicle": "Toyota Camry", "passenger_capacity": 3, "phone": f"+1415555010{user_id}", "eligibility_acknowledged": True}
        payload.update(updates)
        return self.client.put("/rides/driver-profile", json=payload, headers=self.headers(user_id))

    def offer(self, ride_id, user_id=2, **updates):
        payload = {"pickup_time": (self.start + timedelta(minutes=10)).isoformat(), "amount": "12.50", "message": "Room for both bags"}
        payload.update(updates)
        return self.client.post(f"/rides/requests/{ride_id}/offers", json=payload, headers=self.headers(user_id))

    def seed_offer(self):
        ride = self.create()
        self.assertEqual(ride.status_code, 201, ride.text)
        self.assertEqual(self.driver().status_code, 200)
        ride_id = ride.json()["id"]
        offer = self.offer(ride_id)
        self.assertEqual(offer.status_code, 201, offer.text)
        return ride_id, offer.json()["offers"][0]["id"]

    def confirm(self, ride_id, offer_id, user_id=1):
        return self.client.post(f"/rides/requests/{ride_id}/confirm", json={"offer_id": offer_id}, headers=self.headers(user_id))

    def test_auth_required(self):
        self.assertEqual(self.client.get("/rides/requests").status_code, 401)
        self.assertEqual(self.client.get("/rides/mine").status_code, 401)
        self.assertEqual(self.client.get("/rides/driver-profile").status_code, 401)

    def test_member_browsing_and_location_resolution(self):
        ride = self.create()
        self.assertEqual(ride.status_code, 201, ride.text)
        ride_id = ride.json()["id"]
        self.assertNotIn("rider_phone", ride.json())
        self.assertEqual(self.client.get("/rides/requests", headers=self.headers(2)).status_code, 200)
        detail = self.client.get(f"/rides/requests/{ride_id}", headers=self.headers(2))
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["offers"], [])
        self.assertIsNone(detail.json()["booking"])
        responses = [
            detail.json()["request"],
            self.client.get("/rides/requests", headers=self.headers(2)).json()[0],
            self.map_search().json()["rides"][0],
            self.client.post("/rides/requests/table-search", json={}, headers=self.headers(2)).json()["rides"][0],
        ]
        for response in responses:
            for field in ("pickup", "dropoff"):
                self.assertEqual(response[field], place(field).model_dump())
            self.assertNotIn("phone", str(response))
        self.assertEqual(ride.json()["pickup"]["location"], "Exact address: pickup")
        self.driver()
        results = self.client.get("/rides/requests", headers=self.headers(2))
        self.assertEqual(results.status_code, 200, results.text)
        self.assertEqual(results.json()[0]["pickup"]["location"], "Exact address: pickup")
        self.assertNotIn("rider_phone", results.json()[0])
        self.assertTrue(results.json()[0]["pickup_start"].endswith("+00:00"))

    def test_phone_profile_and_consent_validation(self):
        for updates in ({"phone": "12345678"}, {"vehicle": " "}, {"passenger_capacity": 0}, {"eligibility_acknowledged": False}):
            self.assertEqual(self.driver(**updates).status_code, 422)
        self.assertEqual(self.create(exact_location_consent=False).status_code, 422)
        self.assertEqual(self.create(rider_phone="not a number").status_code, 422)
        self.assertEqual(self.client.get("/rides/driver-profile", headers=self.headers(2)).json(), None)

    def test_invalid_request_windows_and_locations(self):
        for updates in (
            {"pickup_start": "2020-01-01T00:00:00Z"},
            {"pickup_end": (self.start - timedelta(minutes=1)).isoformat()},
            {"pickup_end": (self.start + timedelta(hours=3)).isoformat()},
            {"pickup_start": self.start.replace(tzinfo=None).isoformat()},
            {"timezone": "Bad/Timezone"}, {"pickup_location_id": "dropoff"}, {"passengers": 9},
        ):
            response = self.create(**updates)
            self.assertEqual(response.status_code, 422, response.text)

    def test_provider_failure_does_not_create_request(self):
        with patch("app.services.rides.resolve_post_location", side_effect=HTTPException(502, "Location provider failed")):
            response = self.create()
        self.assertEqual(response.status_code, 502)
        with Session(self.engine) as db:
            self.assertEqual(list(db.scalars(select(RideRequest))), [])

    def test_offer_requires_profile_and_prevents_self_offer(self):
        ride_id = self.create().json()["id"]
        self.assertEqual(self.offer(ride_id).status_code, 403)
        self.driver(1)
        self.assertEqual(self.offer(ride_id, 1).status_code, 403)

    def test_offer_capacity_time_and_amount(self):
        ride_id = self.create(passengers=4).json()["id"]
        self.driver()
        self.assertEqual(self.offer(ride_id).status_code, 422)
        self.driver(passenger_capacity=4)
        for updates in (
            {"pickup_time": (self.start - timedelta(seconds=1)).isoformat()},
            {"pickup_time": (self.end + timedelta(seconds=1)).isoformat()},
            {"amount": "-1"}, {"amount": "1.001"}, {"amount": "10000"}, {"amount": "NaN"}, {"message": " "},
        ):
            self.assertEqual(self.offer(ride_id, **updates).status_code, 422)
        self.assertEqual(self.offer(ride_id, amount="0").status_code, 201)
        self.assertEqual(self.offer(ride_id).status_code, 409)

    def test_offer_visibility_withdraw_and_reoffer(self):
        ride_id, offer_id = self.seed_offer()
        self.driver(3)
        self.assertEqual(self.offer(ride_id, 3).status_code, 201)
        for user_id, count in ((1, 2), (2, 1), (3, 1)):
            response = self.client.get(f"/rides/requests/{ride_id}", headers=self.headers(user_id))
            self.assertEqual(len(response.json()["offers"]), count)
            self.assertNotIn("phone", str(response.json()))
        path = f"/rides/requests/{ride_id}/offers/{offer_id}/withdraw"
        self.assertEqual(self.client.post(path, headers=self.headers(3)).status_code, 404)
        self.assertEqual(self.client.post(path, headers=self.headers(2)).status_code, 200)
        self.assertEqual(self.confirm(ride_id, offer_id).status_code, 409)
        self.assertEqual(self.offer(ride_id, amount="20").status_code, 201)
        self.assertEqual(self.confirm(ride_id, offer_id).status_code, 200)

    def test_confirm_snapshot_contact_privacy_and_idempotency(self):
        ride_id, offer_id = self.seed_offer()
        self.driver(3)
        second = self.offer(ride_id, 3).json()["offers"][0]["id"]
        self.assertEqual(self.confirm(ride_id, offer_id, 2).status_code, 403)
        result = self.confirm(ride_id, offer_id)
        self.assertEqual(result.status_code, 200, result.text)
        booking = result.json()["booking"]
        self.assertEqual(booking["driver_phone"], "+14155550102")
        self.assertEqual(booking["rider_phone"], "+14155550101")
        self.assertEqual(booking["amount"], "12.50")
        self.assertEqual([offer["status"] for offer in result.json()["offers"]], ["ACCEPTED", "NOT_SELECTED"])
        self.assertEqual(self.confirm(ride_id, offer_id).json()["booking"]["id"], booking["id"])
        self.assertEqual(self.confirm(ride_id, second).status_code, 409)
        self.driver(vehicle="New car", phone="+14155550999")
        driver_detail = self.client.get(f"/rides/requests/{ride_id}", headers=self.headers(2)).json()
        self.assertEqual(driver_detail["booking"]["driver_phone"], "+14155550102")
        self.assertEqual(driver_detail["booking"]["vehicle"], "Toyota Camry")
        losing_driver = self.client.get(f"/rides/requests/{ride_id}", headers=self.headers(3)).json()
        self.assertIsNone(losing_driver["booking"])
        self.assertNotIn("+141555501", str(losing_driver))
        self.driver(4)
        self.assertEqual(self.client.get(f"/rides/requests/{ride_id}", headers=self.headers(4)).status_code, 404)
        self.assertEqual(self.offer(ride_id, 3).status_code, 409)
        with Session(self.engine) as db:
            self.assertEqual(len(list(db.scalars(select(RideBooking)))), 1)

    def test_confirm_rechecks_driver_eligibility(self):
        ride_id, offer_id = self.seed_offer()
        with Session(self.engine) as db:
            profile = db.get(DriverProfile, 2)
            db.delete(profile)
            db.commit()
        self.assertEqual(self.confirm(ride_id, offer_id).status_code, 403)
        self.assertIsNone(self.client.get(f"/rides/requests/{ride_id}", headers=self.headers()).json()["booking"])

    def test_confirm_rechecks_capacity(self):
        ride_id = self.create(passengers=3).json()["id"]
        self.driver(passenger_capacity=3)
        offer_id = self.offer(ride_id).json()["offers"][0]["id"]
        self.driver(passenger_capacity=2)
        self.assertEqual(self.confirm(ride_id, offer_id).status_code, 409)

    def test_expired_offer_can_be_resubmitted_while_window_open(self):
        ride_id, offer_id = self.seed_offer()
        with Session(self.engine) as db:
            ride = db.get(RideRequest, ride_id)
            ride.pickup_start = datetime.utcnow() - timedelta(minutes=5)
            ride.pickup_end = datetime.utcnow() + timedelta(minutes=25)
            offer = db.get(RideOffer, offer_id)
            offer.pickup_time = datetime.utcnow() - timedelta(minutes=1)
            db.commit()
        detail = self.client.get(f"/rides/requests/{ride_id}", headers=self.headers(2)).json()
        self.assertEqual(detail["request"]["status"], "OPEN")
        self.assertEqual(detail["offers"][0]["status"], "EXPIRED")
        self.assertEqual(self.confirm(ride_id, offer_id).status_code, 409)
        response = self.offer(ride_id, pickup_time=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat())
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["offers"][0]["id"], offer_id)
        self.assertEqual(self.confirm(ride_id, offer_id).status_code, 200)

    def test_cancel_request_closes_offers(self):
        ride_id, offer_id = self.seed_offer()
        path = f"/rides/requests/{ride_id}/cancel"
        self.assertEqual(self.client.post(path, headers=self.headers(2)).status_code, 403)
        response = self.client.post(path, headers=self.headers())
        self.assertEqual(response.json()["request"]["status"], "CANCELLED")
        self.assertEqual(response.json()["offers"][0]["status"], "NOT_SELECTED")
        self.assertEqual(self.client.post(path, headers=self.headers()).status_code, 200)
        self.assertEqual(self.confirm(ride_id, offer_id).status_code, 409)

    def test_cancel_booking_requires_participant_and_reason(self):
        ride_id, offer_id = self.seed_offer()
        self.confirm(ride_id, offer_id)
        self.driver(3)
        path = f"/rides/requests/{ride_id}/booking/cancel"
        self.assertEqual(self.client.post(path, json={"reason": "Unavailable"}, headers=self.headers(3)).status_code, 404)
        self.assertEqual(self.client.post(path, json={"reason": " "}, headers=self.headers(2)).status_code, 422)
        response = self.client.post(path, json={"reason": "Vehicle unavailable"}, headers=self.headers(2))
        self.assertEqual(response.json()["booking"]["status"], "CANCELLED")
        self.assertEqual(response.json()["request"]["status"], "CANCELLED")
        self.assertEqual(self.confirm(ride_id, offer_id).status_code, 409)

    def test_completion_only_rider_after_pickup(self):
        ride_id, offer_id = self.seed_offer()
        self.confirm(ride_id, offer_id)
        path = f"/rides/requests/{ride_id}/booking/complete"
        self.assertEqual(self.client.post(path, headers=self.headers(2)).status_code, 403)
        self.assertEqual(self.client.post(path, headers=self.headers()).status_code, 409)
        with Session(self.engine) as db:
            ride = db.get(RideRequest, ride_id)
            ride.pickup_start = datetime.utcnow() - timedelta(hours=2)
            ride.pickup_end = datetime.utcnow() - timedelta(hours=1)
            db.commit()
        response = self.client.post(path, headers=self.headers())
        self.assertEqual(response.json()["booking"]["status"], "COMPLETED")
        self.assertEqual(self.client.get("/rides/mine", headers=self.headers()).json()[0]["booking_status"], "COMPLETED")
        self.assertEqual(self.client.post(path, headers=self.headers()).status_code, 200)
        self.assertEqual(self.client.post(path, headers=self.headers(2)).status_code, 403)
        self.assertEqual(self.client.post(f"/rides/requests/{ride_id}/booking/cancel", json={"reason": "Too late"}, headers=self.headers()).status_code, 409)

    def test_expiration_excludes_browse_and_blocks_confirmation(self):
        ride_id, offer_id = self.seed_offer()
        with Session(self.engine) as db:
            ride = db.get(RideRequest, ride_id)
            ride.pickup_start = datetime.utcnow() - timedelta(hours=2)
            ride.pickup_end = datetime.utcnow() - timedelta(hours=1)
            db.commit()
        self.assertEqual(self.client.get("/rides/requests", headers=self.headers(2)).json(), [])
        response = self.client.get(f"/rides/requests/{ride_id}", headers=self.headers())
        self.assertEqual(response.json()["request"]["status"], "EXPIRED")
        self.assertEqual(response.json()["offers"][0]["status"], "EXPIRED")
        self.assertEqual(self.confirm(ride_id, offer_id).status_code, 409)

    def test_search_location_radius_local_date_and_pagination(self):
        self.create()
        self.create(pickup_location_id="far")
        self.driver()
        response = self.client.get("/rides/requests?pickup_location_id=pickup&radius_km=10&limit=1", headers=self.headers(2))
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["pickup"]["location_id"], "pickup")
        response = self.client.get("/rides/requests?pickup_location_id=pickup&radius_km=10&offset=1", headers=self.headers(2))
        self.assertEqual(response.json(), [])
        self.assertEqual(len(self.client.get("/rides/requests?dropoff_location_id=dropoff", headers=self.headers(2)).json()), 2)
        self.assertEqual(self.client.get("/rides/requests?departure_date=2020-01-01", headers=self.headers(2)).json(), [])
        self.assertEqual(self.client.get("/rides/requests?limit=100", headers=self.headers(2)).status_code, 422)
        from zoneinfo import ZoneInfo
        local_date = self.start.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
        self.assertEqual(len(self.client.get(f"/rides/requests?departure_date={local_date}", headers=self.headers(2)).json()), 2)

    def test_my_rides_includes_own_requests_and_driver_offers_only(self):
        ride_id, _ = self.seed_offer()
        for user_id, count in ((1, 1), (2, 1), (3, 0)):
            response = self.client.get("/rides/mine", headers=self.headers(user_id))
            self.assertEqual(len(response.json()), count)
            self.assertNotIn("phone", str(response.json()))
        self.assertEqual(self.client.get("/rides/mine?offset=1", headers=self.headers()).json(), [])

    def test_existing_post_feed_still_works(self):
        response = self.client.get("/posts", headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [])

    def map_search(self, user_id=2, **updates):
        payload = {
            "bounds": {"north": 37.6, "south": 37.5, "west": -122.05, "east": -121.9},
            "limit": 50,
        }
        payload.update(updates)
        return self.client.post("/rides/requests/search", json=payload, headers=self.headers(user_id))

    def test_map_search_permissions_and_exact_pickup_bounds(self):
        ride_id = self.create().json()["id"]
        self.assertEqual(self.client.post("/rides/requests/search", json={}).status_code, 401)
        self.assertEqual(self.map_search().status_code, 200)
        self.driver()
        response = self.map_search()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([ride["id"] for ride in response.json()["rides"]], [ride_id])
        self.assertFalse(response.json()["has_more"])
        self.assertNotIn("phone", str(response.json()))
        self.driver(1)
        self.assertEqual(self.map_search(1).json()["rides"], [])
        # The request's drop-off is outside the viewport but must not exclude it.
        self.assertGreater(place("dropoff").latitude, 37.6)
        self.assertEqual(self.map_search(bounds={"north": 37.64, "south": 37.61, "west": -122.4, "east": -122.35}).json()["rides"], [])

    def test_map_search_filters_before_result_limit_and_has_more(self):
        self.create(dropoff_location_id="far")
        first_matching = self.create().json()["id"]
        self.create()
        self.driver()
        response = self.map_search(dropoff_location_id="dropoff", radius_km=10, limit=1)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([ride["id"] for ride in response.json()["rides"]], [first_matching])
        self.assertTrue(response.json()["has_more"])
        self.assertEqual(len(self.map_search(dropoff_location_id="dropoff", radius_km=10).json()["rides"]), 2)
        self.assertEqual(self.map_search(departure_date="2020-01-01").json()["rides"], [])
        from zoneinfo import ZoneInfo
        date = self.start.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
        self.assertEqual(len(self.map_search(departure_date=date).json()["rides"]), 3)

    def test_map_search_validation_and_large_area_limits(self):
        self.driver()
        for updates in (
            {"bounds": {"north": 38, "south": 39, "west": -122, "east": -121}},
            {"bounds": {"north": 80, "south": -80, "west": -170, "east": 170}},
            {"bounds": {"north": 91, "south": 37, "west": -122, "east": -121}},
            {"limit": 51}, {"radius_km": 101}, {"dropoff_location_id": " "},
            {"pickup_time_from": "09:00", "pickup_time_to": "10:00"},
            {"departure_date": "2030-01-02", "pickup_time_from": "09:00"},
            {"departure_date": "2030-01-02", "pickup_time_to": "10:00"},
            {"departure_date": "2030-01-02", "pickup_time_from": "10:00", "pickup_time_to": "09:00"},
            {"departure_date": "2030-01-02", "pickup_time_from": "09:00", "pickup_time_to": "09:00"},
            {"departure_date": "2030-01-02", "pickup_time_from": "09:00Z", "pickup_time_to": "10:00Z"},
        ):
            response = self.map_search(**updates)
            self.assertEqual(response.status_code, 422, response.text)

    def test_map_time_range_overlaps_before_limit_in_each_ride_timezone(self):
        day = (self.start + timedelta(days=3)).date().isoformat()
        from zoneinfo import ZoneInfo

        def seed(start_time, end_time, zone):
            start = datetime.fromisoformat(f"{day}T{start_time}").replace(tzinfo=ZoneInfo(zone))
            end = datetime.fromisoformat(f"{day}T{end_time}").replace(tzinfo=ZoneInfo(zone))
            response = self.create(pickup_start=start.isoformat(), pickup_end=end.isoformat(), timezone=zone)
            self.assertEqual(response.status_code, 201, response.text)
            return response.json()["id"]

        seed("07:00", "08:00", "America/New_York")
        ny = seed("08:45", "09:15", "America/New_York")
        la = seed("09:30", "10:30", "America/Los_Angeles")
        edge = seed("10:00", "10:00", "America/Los_Angeles")
        seed("10:01", "11:00", "America/Los_Angeles")
        self.driver()
        filters = {"departure_date": day, "pickup_time_from": "09:00", "pickup_time_to": "10:00"}
        response = self.map_search(**filters)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([ride["id"] for ride in response.json()["rides"]], [ny, la, edge])
        limited = self.map_search(**filters, limit=1).json()
        self.assertEqual([ride["id"] for ride in limited["rides"]], [ny])
        self.assertTrue(limited["has_more"])
        self.assertEqual(len(self.map_search(departure_date=day).json()["rides"]), 5)
        self.assertEqual(len(self.map_search().json()["rides"]), 5)

    def test_map_whole_day_includes_cross_midnight_window_not_next_midnight(self):
        from zoneinfo import ZoneInfo
        zone = ZoneInfo("America/Los_Angeles")
        day = (self.start + timedelta(days=3)).date()
        midnight = datetime.combine(day, datetime.min.time(), zone)
        crossing = self.create(
            pickup_start=(midnight - timedelta(minutes=30)).isoformat(),
            pickup_end=(midnight + timedelta(minutes=30)).isoformat(),
        ).json()["id"]
        self.create(
            pickup_start=(midnight + timedelta(days=1)).isoformat(),
            pickup_end=(midnight + timedelta(days=1, minutes=30)).isoformat(),
        )
        self.driver()
        response = self.map_search(departure_date=day.isoformat())
        self.assertEqual([ride["id"] for ride in response.json()["rides"]], [crossing])

    def test_map_time_range_matches_both_daylight_saving_repeated_hours(self):
        from zoneinfo import ZoneInfo
        zone = ZoneInfo("America/New_York")
        year = self.start.year + 1
        day = datetime(year, 11, 1)
        while day.weekday() != 6:
            day += timedelta(days=1)
        ids = []
        for fold in (0, 1):
            start = day.replace(hour=1, minute=15, tzinfo=zone, fold=fold)
            response = self.create(pickup_start=start.isoformat(), pickup_end=start.isoformat(), timezone=zone.key)
            self.assertEqual(response.status_code, 201, response.text)
            ids.append(response.json()["id"])
        self.driver()
        response = self.map_search(departure_date=day.date().isoformat(), pickup_time_from="01:00", pickup_time_to="01:30")
        self.assertEqual([ride["id"] for ride in response.json()["rides"]], ids)

    def test_map_search_exact_boundary_filters_h3_false_positives(self):
        ride_id = self.create().json()["id"]
        self.driver()
        bounds = {"north": 37.5501, "south": 37.5499, "west": -121.9801, "east": -121.9799}
        self.assertEqual(len(self.map_search(bounds=bounds).json()["rides"]), 1)
        with Session(self.engine) as db:
            ride = db.get(RideRequest, ride_id)
            # Keep a candidate H3 cell but move coordinates outside the tiny viewport.
            pickup = dict(ride.pickup)
            pickup["latitude"] = 37.551
            pickup["h3_cell_id"] = h3.latlng_to_cell(37.551, -121.98, 8)
            ride.pickup = pickup
            db.commit()
        self.assertEqual(self.map_search(bounds=bounds).json()["rides"], [])
        edge = {"north": 37.551, "south": 37.55, "west": -121.98, "east": -121.97}
        self.assertEqual(len(self.map_search(bounds=edge).json()["rides"]), 1)

    def test_map_search_excludes_expired_cancelled_and_confirmed_requests(self):
        confirmed_id, offer_id = self.seed_offer()
        self.confirm(confirmed_id, offer_id)
        cancelled_id = self.create().json()["id"]
        self.client.post(f"/rides/requests/{cancelled_id}/cancel", headers=self.headers())
        expired_id = self.create().json()["id"]
        with Session(self.engine) as db:
            ride = db.get(RideRequest, expired_id)
            ride.pickup_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
            ride.pickup_end = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
            db.commit()
        self.assertEqual(self.map_search().json(), {"rides": [], "has_more": False})

    def test_map_search_crosses_antimeridian(self):
        ids = [self.create().json()["id"] for _ in range(3)]
        self.driver()
        with Session(self.engine) as db:
            for ride_id, longitude in zip(ids, (179.9, -179.9, 0)):
                ride = db.get(RideRequest, ride_id)
                pickup = dict(ride.pickup)
                pickup.update(latitude=0.0, longitude=longitude, h3_cell_id=h3.latlng_to_cell(0, longitude, 8))
                ride.pickup = pickup
            db.commit()
        response = self.map_search(bounds={"north": 0.05, "south": -0.05, "west": 179.8, "east": -179.8})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([ride["id"] for ride in response.json()["rides"]], ids[:2])

    def test_map_destination_radius_enforces_25_km(self):
        ids = [self.create().json()["id"] for _ in range(2)]
        self.driver()
        destination = place("dropoff")
        with Session(self.engine) as db:
            for ride_id, distance in zip(ids, (24.99, 25.01)):
                ride = db.get(RideRequest, ride_id)
                dropoff = dict(ride.dropoff)
                dropoff["latitude"] = destination.latitude + degrees(distance / 6371)
                ride.dropoff = dropoff
            db.commit()
        response = self.map_search(dropoff_location_id="dropoff", radius_km=25)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([ride["id"] for ride in response.json()["rides"]], ids[:1])

    def test_map_destination_provider_error_is_explicit(self):
        self.driver()
        with patch("app.api.rides.resolve_post_location", side_effect=HTTPException(502, "Location provider failed")):
            response = self.map_search(dropoff_location_id="dropoff")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "Location provider failed")


if __name__ == "__main__":
    unittest.main()
