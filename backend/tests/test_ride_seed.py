import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import h3
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.ride_time import utc_now_naive
from app.db.base import Base
from app.db.url import parse_database_url
from app.models.carpool import CarpoolSeatRequest, CarpoolTrip
from app.models.ride import DriverProfile, RideBooking, RideOffer, RideRequest
from app.models.user import User
from app.schemas.location import LocationSearchResponse
from app.schemas.post import PostLocationFields
from scripts.seed_rides import (
    CARPOOLS, LOCATIONS, REQUESTS, build_request, build_trip, sample_id,
    seed_rides, validate_local_database, validate_migrations,
)


class RideSeedTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.owner = User(id=uuid4(), name="Test owner", email="owner@example.test",
                          provider="test", provider_id="owner")
        self.other = User(id=uuid4(), name="Other", email="other@example.test",
                          provider="test", provider_id="other")
        self.profile = DriverProfile(
            user_id=self.owner.id, vehicle="Test vehicle", vehicle_color="Blue",
            passenger_capacity=2, phone="+14155550123", license_plate="TEST",
            acknowledgement_at=utc_now_naive(),
        )
        self.db.add_all([self.owner, self.other, self.profile])
        self.db.commit()
        self.locations = {
            area: PostLocationFields(
                location_id=area, location=f"Public landmark, {area}, CA", city=area,
                state="CA", country_code="US", postal_code="90000", latitude=lat,
                longitude=lng, h3_cell_id=h3.latlng_to_cell(lat, lng, 8),
            ) for area, _, lat, lng in LOCATIONS
        }
        self.search = patch("scripts.seed_rides.search_locations", side_effect=self.search_location)
        self.resolve = patch("scripts.seed_rides.resolve_post_location", side_effect=self.locations.__getitem__)
        self.search.start()
        self.resolve.start()
        self.addCleanup(self.search.stop)
        self.addCleanup(self.resolve.stop)

    def search_location(self, request):
        area = next(area for area, query, _, _ in LOCATIONS if query == request.query)
        return LocationSearchResponse(status="success", data=[{"id": area, "addressLine1": request.query}])

    def seed(self):
        # A lookup starts the same transaction main uses before seeding.
        owner = self.db.get(User, self.owner.id)
        result = seed_rides(self.db, owner)
        self.db.commit()
        return result

    def count(self, model):
        return self.db.scalar(select(func.count()).select_from(model))

    def test_valid_future_varied_samples_reuse_real_profile_and_link_return(self):
        self.assertEqual(self.seed(), (6, 0, 6, 0))
        trips = list(self.db.scalars(select(CarpoolTrip)))
        requests = list(self.db.scalars(select(RideRequest)))
        now = utc_now_naive()
        self.assertEqual(len({row.id for row in trips + requests}), 12)
        self.assertEqual({row.seats for row in trips}, {1, 2})
        self.assertEqual({row.passengers for row in requests}, {1, 2, 3, 4})
        self.assertEqual({row.bags_per_person for row in trips}, {0, 1, 2})
        self.assertEqual({int((row.pickup_end - row.pickup_start).total_seconds() / 60)
                          for row in requests}, {30, 60, 120})
        self.assertTrue(any(row.preferred_amount is None for row in requests))
        self.assertTrue(any(row.preferred_amount == 0 for row in requests))
        for row in trips + requests:
            self.assertGreater(row.pickup_start, now)
            self.assertEqual(row.status, "OPEN")
            self.assertEqual(row.timezone, "America/Los_Angeles")
            self.assertTrue(row.notes.startswith("[Demo] FICTIONAL SAMPLE ONLY"))
            self.assertNotEqual(row.pickup["location_id"], row.dropoff["location_id"])
            PostLocationFields.model_validate(row.pickup)
            for place in (row.pickup, row.dropoff):
                self.assertEqual(place["h3_cell_id"], h3.latlng_to_cell(place["latitude"], place["longitude"], 8))
        for trip in trips:
            self.assertEqual(trip.driver_id, self.owner.id)
            self.assertEqual(trip.vehicle, self.profile.vehicle)
            self.assertEqual(trip.vehicle_color, self.profile.vehicle_color)
            self.assertEqual(trip.driver_license_plate, self.profile.license_plate)
            self.assertLessEqual(trip.seats, self.profile.passenger_capacity)
        self.assertTrue(all(row.rider_phone == self.profile.phone for row in requests))
        outbound = self.db.get(CarpoolTrip, sample_id(self.owner.id, "carpool", 0))
        returning = self.db.get(CarpoolTrip, sample_id(self.owner.id, "carpool", 1))
        self.assertEqual(returning.outbound_id, outbound.id)
        self.assertGreater(returning.pickup_start, outbound.pickup_end)
        self.assertEqual(returning.pickup, outbound.dropoff)
        for model in (CarpoolSeatRequest, RideOffer, RideBooking):
            self.assertEqual(self.count(model), 0)
        self.assertEqual(self.count(User), 2)
        self.assertEqual(self.count(DriverProfile), 1)

    def test_repeat_seed_preserves_all_existing_data_and_avoids_provider(self):
        now = utc_now_naive()
        unrelated = build_request(0, self.other, self.profile, self.locations, now)
        unrelated.id = uuid4()
        self.db.add(unrelated)
        self.db.commit()
        self.seed()
        trip = self.db.get(CarpoolTrip, sample_id(self.owner.id, "carpool", 0))
        request = self.db.get(RideRequest, sample_id(self.owner.id, "request", 0))
        trip.notes, request.notes = "Owner edited carpool", "Owner edited request"
        trip.status, request.status = "CANCELLED", "CANCELLED"
        profile_before = {column.name: getattr(self.profile, column.name)
                          for column in DriverProfile.__table__.columns}
        self.db.commit()
        with patch("scripts.seed_rides.search_locations") as search:
            self.assertEqual(self.seed(), (0, 6, 0, 6))
            search.assert_not_called()
        self.assertEqual(trip.notes, "Owner edited carpool")
        self.assertEqual(request.notes, "Owner edited request")
        self.assertEqual(trip.status, "CANCELLED")
        self.assertEqual(request.status, "CANCELLED")
        self.assertEqual(self.count(RideRequest), 7)
        self.assertEqual(self.count(CarpoolTrip), 6)
        self.assertEqual(profile_before, {column.name: getattr(self.profile, column.name)
                                         for column in DriverProfile.__table__.columns})
        self.assertEqual(unrelated.rider_id, self.other.id)

    def test_absent_or_unacknowledged_driver_blocks_without_writes(self):
        self.profile.acknowledgement_at = None
        with self.db.no_autoflush, self.assertRaisesRegex(RuntimeError, "driver profile"):
            seed_rides(self.db, self.owner)
        self.db.rollback()
        self.db.delete(self.profile)
        self.db.commit()
        with patch("scripts.seed_rides.search_locations") as search:
            with self.assertRaisesRegex(RuntimeError, "driver profile"):
                seed_rides(self.db, self.owner)
            search.assert_not_called()
        self.assertEqual(self.count(CarpoolTrip), 0)
        self.assertEqual(self.count(RideRequest), 0)

    def test_invalid_real_profile_blocks_without_replacing_details(self):
        self.profile.phone = "invalid"
        with self.assertRaises(ValueError):
            seed_rides(self.db, self.owner)
        self.assertEqual(self.profile.phone, "invalid")
        self.assertEqual(self.count(CarpoolTrip), 0)

    def test_provider_empty_or_wrong_region_inserts_nothing(self):
        with patch("scripts.seed_rides.search_locations",
                   return_value=LocationSearchResponse(status="success", data=[])):
            with self.assertRaisesRegex(RuntimeError, "No provider location"):
                seed_rides(self.db, self.owner)
        with patch("scripts.seed_rides.resolve_post_location",
                   return_value=self.locations["Los Angeles"]):
            with self.assertRaisesRegex(RuntimeError, "Unexpected provider landmark"):
                seed_rides(self.db, self.owner)
        self.assertEqual(self.count(CarpoolTrip), 0)
        self.assertEqual(self.count(RideRequest), 0)

    def test_failure_after_trip_flush_rolls_back_whole_batch(self):
        owner_id = self.owner.id
        self.db.rollback()
        with self.assertRaisesRegex(RuntimeError, "late failure"):
            with self.db.begin():
                owner = self.db.get(User, owner_id)
                with patch("scripts.seed_rides.build_request", side_effect=RuntimeError("late failure")):
                    seed_rides(self.db, owner)
        self.assertEqual(self.count(CarpoolTrip), 0)
        self.assertEqual(self.count(RideRequest), 0)

    def test_foreign_owner_id_collision_is_blocked(self):
        trip = build_trip(0, self.owner, self.profile, self.locations, utc_now_naive())
        trip.driver_id = self.other.id
        self.db.add(trip)
        self.db.commit()
        with self.assertRaisesRegex(RuntimeError, "another user"):
            seed_rides(self.db, self.owner)
        self.assertEqual(self.count(CarpoolTrip), 1)
        self.assertEqual(self.count(RideRequest), 0)

    def test_missing_sample_can_be_reinserted_without_overwriting_others(self):
        self.seed()
        self.db.delete(self.db.get(RideRequest, sample_id(self.owner.id, "request", 2)))
        self.db.commit()
        self.assertEqual(self.seed(), (0, 6, 1, 5))

    def test_local_postgresql_guard_blocks_remote_and_overrides(self):
        with patch.dict(os.environ, {}, clear=True):
            for url in ("postgresql://localhost/demo", "postgresql://127.0.0.1/demo", "postgresql://[::1]/demo"):
                validate_local_database(parse_database_url(url))
            for url in ("sqlite://", "postgresql://remote.example/demo",
                        "postgresql:///demo", "postgresql://localhost/demo?host=remote.example",
                        "postgresql://localhost/demo?hostaddr=8.8.8.8",
                        "postgresql://localhost/demo?service=remote"):
                with self.subTest(url=url), self.assertRaisesRegex(RuntimeError, "local PostgreSQL"):
                    validate_local_database(parse_database_url(url))
            with patch.dict(os.environ, {"PGHOSTADDR": "8.8.8.8"}):
                with self.assertRaises(RuntimeError):
                    validate_local_database(parse_database_url("postgresql://localhost/demo"))

    def test_migrations_require_exact_current_heads(self):
        with patch("scripts.seed_rides.ScriptDirectory") as scripts:
            scripts.return_value.get_heads.return_value = ["head"]
            with patch.object(self.db, "scalars", return_value=iter(["old"])):
                with self.assertRaisesRegex(RuntimeError, "Alembic head"):
                    validate_migrations(self.db)
            with patch.object(self.db, "scalars", return_value=iter(["head", "unexpected"])):
                with self.assertRaises(RuntimeError):
                    validate_migrations(self.db)
            with patch.object(self.db, "scalars", return_value=iter(["head"])):
                validate_migrations(self.db)


if __name__ == "__main__":
    unittest.main()
