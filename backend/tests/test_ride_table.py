import os
import unittest
from datetime import datetime, timedelta, timezone
from math import degrees
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.api.rides import router
from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.dependencies import get_db
from app.models.ride import DriverProfile, RideRequest
from app.models.user import User
from app.schemas.ride import RideTableSearchInput
from app.services.ride_search import pickup_radius_cells
from test_rides import place


class TableInputTests(unittest.TestCase):
    def test_invalid_ranges_and_limits(self):
        from pydantic import ValidationError
        for data in (
            {"radius_km": 101}, {"radius_km": 0}, {"radius_km": float("nan")},
            {"radius_km": float("inf")}, {"max_passengers": 0}, {"limit": 51},
            {"pickup_time_from": "09:00", "pickup_time_to": "10:00"},
            {"departure_date": "2030-01-02", "pickup_time_from": "10:00", "pickup_time_to": "09:00"},
            {"cursor": {"id": 0, "pickup_start": "2030-01-02"}},
            {"dropoff_location_id": "unused"},
        ):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                RideTableSearchInput.model_validate(data)

    def test_fractional_mile_conversions_are_preserved(self):
        for miles in (5, 10, 25, 50):
            radius = miles * 1.609344
            data = RideTableSearchInput.model_validate({"radius_km": radius})
            self.assertEqual(data.radius_km, radius)

    def test_radius_cover_contains_boundary_cells(self):
        import h3
        for lat, lng in ((37.55, -121.98), (0, 179.99), (89.8, 0), (-89.8, 0)):
            pickup = place("pickup").model_copy(update={"latitude": lat, "longitude": lng})
            for radius in (25, 100, 5 * 1.609344, 10 * 1.609344, 25 * 1.609344, 50 * 1.609344):
                with self.subTest(latitude=lat, longitude=lng, radius=radius):
                    cells = pickup_radius_cells(pickup, radius)
                    self.assertIn(h3.latlng_to_cell(lat, lng, 8), cells)
                    for delta in (-1, 1):
                        target = max(-90, min(90, lat + delta * degrees((radius - 0.01) / 6371)))
                        self.assertIn(h3.latlng_to_cell(target, lng, 8), cells)


@unittest.skipUnless(os.getenv("RIDE_TEST_POSTGRES") == "1", "Set RIDE_TEST_POSTGRES=1 for PostgreSQL table-search tests")
class PostgreSQLTableTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.schema = "ride_test_" + uuid4().hex
        with self.engine.begin() as connection:
            connection.execute(CreateSchema(self.schema))
        self.isolated = self.engine.execution_options(schema_translate_map={None: self.schema})
        Base.metadata.create_all(self.isolated)
        self.addCleanup(self.cleanup_database)
        with Session(self.isolated) as db:
            for id in (1, 2, 3):
                db.add(User(id=id, email=f"{id}@example.test", name=f"Member {id}", provider="test", provider_id=str(id)))
            db.commit()
            db.add(DriverProfile(user_id=2, vehicle="Test", passenger_capacity=4, phone="+14155550102", acknowledgement_at=datetime.now()))
            db.commit()
        app = FastAPI()
        app.include_router(router, prefix="/rides")

        def db_session():
            with Session(self.isolated) as db:
                yield db
        app.dependency_overrides[get_db] = db_session
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.patch = patch("app.api.rides.resolve_post_location", side_effect=place)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.start = (datetime.now(timezone.utc) + timedelta(days=5)).replace(hour=17, minute=0, second=0, microsecond=0)

    def cleanup_database(self):
        with self.engine.begin() as connection:
            connection.execute(DropSchema(self.schema, cascade=True))
        self.engine.dispose()

    def seed(self, *, minutes=0, passengers=1, distance=None, rider=1, status="OPEN", zone="America/Los_Angeles"):
        import h3
        pickup = place("pickup").model_dump()
        if distance is not None:
            pickup["latitude"] += degrees(distance / 6371)
            pickup["h3_cell_id"] = h3.latlng_to_cell(pickup["latitude"], pickup["longitude"], 8)
        start = (self.start + timedelta(minutes=minutes)).replace(tzinfo=None)
        with Session(self.isolated) as db:
            ride = RideRequest(rider_id=rider, pickup=pickup, dropoff=place("dropoff").model_dump(),
                               pickup_start=start, pickup_end=start + timedelta(minutes=30), timezone=zone,
                               passengers=passengers, bags=1, notes="", rider_phone="+14155550101", currency="USD", status=status)
            db.add(ride)
            db.commit()
            return ride.id

    def search(self, user=2, **data):
        return self.client.post("/rides/requests/table-search", json=data,
                                headers={"Authorization": f"Bearer {create_access_token(user)}"})

    def test_permissions_pagination_and_privacy(self):
        ids = [self.seed() for _ in range(5)]
        self.seed(rider=2)
        self.seed(status="CANCELLED")
        self.assertEqual(self.search(user=3).status_code, 200)
        self.assertEqual(self.client.post("/rides/requests/table-search", json={}).status_code, 401)
        first = self.search(limit=2)
        self.assertEqual(first.status_code, 200, first.text)
        body = first.json()
        self.assertEqual([r["id"] for r in body["rides"]], ids[:2])
        self.assertNotIn("phone", first.text)
        second = self.search(limit=2, cursor=body["next_cursor"]).json()
        self.assertEqual([r["id"] for r in second["rides"]], ids[2:4])
        last = self.search(limit=2, cursor=second["next_cursor"]).json()
        self.assertEqual([r["id"] for r in last["rides"]], ids[4:])
        self.assertFalse(last["has_more"])
        self.assertIsNone(last["next_cursor"])
        self.assertIn("ix_ride_requests_status_pickup_id", [i["name"] for i in inspect(self.engine).get_indexes("ride_requests", schema=self.schema)])

    def test_radius_and_capacity_filter_before_limit(self):
        self.seed(distance=25.01)
        self.seed(passengers=5)
        wanted = self.seed(distance=24.99)
        self.seed(distance=1)
        result = self.search(pickup_location_id="pickup", radius_km=25, max_passengers=2, limit=1)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual([r["id"] for r in result.json()["rides"]], [wanted])
        self.assertTrue(result.json()["has_more"])

    def test_fractional_radius_exact_distance(self):
        radius = 10 * 1.609344
        self.seed(distance=radius + 0.001)
        wanted = self.seed(distance=radius - 0.001)
        result = self.search(pickup_location_id="pickup", radius_km=radius)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual([r["id"] for r in result.json()["rides"]], [wanted])

    def test_date_and_overlap_in_saved_timezones(self):
        from zoneinfo import ZoneInfo
        day = self.start.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
        self.seed(minutes=-120)
        wanted = self.seed(minutes=-15)
        ny = self.seed(zone="America/New_York")
        result = self.search(departure_date=day, pickup_time_from="09:00", pickup_time_to="10:00", limit=1)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual([r["id"] for r in result.json()["rides"]], [wanted])
        self.assertFalse(result.json()["has_more"])
        self.assertEqual(len(self.search(departure_date=day).json()["rides"]), 3)
        self.assertNotEqual(wanted, ny)

    def test_repeated_hour_and_cross_midnight_overlap(self):
        from zoneinfo import ZoneInfo
        zone = ZoneInfo("America/New_York")
        day = datetime(self.start.year + 1, 11, 1)
        while day.weekday() != 6:
            day += timedelta(days=1)
        self.start = day.replace(hour=1, minute=50, tzinfo=zone, fold=0).astimezone(timezone.utc)
        id = self.seed(zone=zone.key)
        result = self.search(departure_date=day.date().isoformat(), pickup_time_from="01:00", pickup_time_to="01:15")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual([r["id"] for r in result.json()["rides"]], [id])
        self.start = (day + timedelta(days=2)).replace(hour=23, minute=45, tzinfo=zone).astimezone(timezone.utc)
        crossing = self.seed(zone=zone.key)
        result = self.search(departure_date=(day + timedelta(days=3)).date().isoformat())
        self.assertEqual([r["id"] for r in result.json()["rides"]], [crossing])
