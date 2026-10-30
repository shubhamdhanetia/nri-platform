import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.api.rides import router
from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.dependencies import get_db
from app.models.ride import DriverProfile, RideBooking, RideOffer, RideRequest
from app.models.notification import Notification
from app.models.user import User
import app.models.post
import app.models.saved_post


@unittest.skipUnless(os.getenv("RIDE_TEST_POSTGRES") == "1", "Set RIDE_TEST_POSTGRES=1 to test in an isolated PostgreSQL schema")
class PostgreSQLConcurrencyTests(unittest.TestCase):
    def test_booking_and_withdrawal_races(self):
        engine = create_engine(settings.DATABASE_URL)
        self.assertEqual(engine.dialect.name, "postgresql")
        schema = "ride_test_" + uuid4().hex
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        isolated = engine.execution_options(schema_translate_map={None: schema})
        try:
            Base.metadata.create_all(isolated)
            indexes = inspect(engine).get_indexes("ride_requests", schema=schema)
            self.assertIn("ix_ride_requests_pickup_h3", [index["name"] for index in indexes])
            app = FastAPI()
            app.include_router(router, prefix="/rides")

            def test_db():
                with Session(isolated, autoflush=False) as db:
                    yield db

            app.dependency_overrides[get_db] = test_db
            with Session(isolated) as db:
                for user_id in (1, 2, 3):
                    db.add(User(id=UUID(int=user_id), email=f"{user_id}@example.test", name=f"Member {user_id}", provider="test", provider_id=str(user_id)))
                db.commit()
                for user_id in (2, 3):
                    db.add(DriverProfile(user_id=UUID(int=user_id), vehicle="Test car", passenger_capacity=3, phone=f"+1415555010{user_id}", acknowledgement_at=datetime.utcnow()))
                db.commit()

            def seed():
                with Session(isolated) as db:
                    start = datetime.utcnow() + timedelta(days=1)
                    ride = RideRequest(rider_id=UUID(int=1), pickup={}, dropoff={}, pickup_start=start, pickup_end=start + timedelta(minutes=30), timezone="UTC", passengers=1, bags=0, notes="", rider_phone="+14155550101", currency="USD")
                    db.add(ride)
                    db.flush()
                    offers = [RideOffer(request_id=ride.id, driver_id=UUID(int=driver_id), pickup_time=start, amount=10, message="Test", vehicle="Test car", passenger_capacity=3) for driver_id in (2, 3)]
                    db.add_all(offers)
                    db.commit()
                    return ride.id, offers[0].id, offers[1].id

            # API responses validate full locations, so seed the same provider-shaped values.
            from test_rides import place
            def locations(ride_id):
                with Session(isolated) as db:
                    ride = db.get(RideRequest, ride_id)
                    ride.pickup = place("pickup").model_dump()
                    ride.dropoff = place("dropoff").model_dump()
                    db.commit()

            rider_headers = {"Authorization": f"Bearer {create_access_token(UUID(int=1))}"}
            driver_headers = {"Authorization": f"Bearer {create_access_token(UUID(int=2))}"}
            with TestClient(app) as client:
                def race(first, second):
                    barrier = Barrier(2)
                    def run(call):
                        barrier.wait(timeout=10)
                        return call()
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        a = executor.submit(run, first)
                        b = executor.submit(run, second)
                        return a.result(timeout=20), b.result(timeout=20)

                ride_id, offer_a, offer_b = seed()
                locations(ride_id)
                response = client.post("/rides/requests/search", json={
                    "bounds": {"north": 37.6, "south": 37.5, "west": -122.05, "east": -121.9},
                }, headers=driver_headers)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual([ride["id"] for ride in response.json()["rides"]], [str(ride_id)])
                self.assertNotIn("phone", str(response.json()))
                confirm_path = f"/rides/requests/{ride_id}/confirm"
                a, b = race(
                    lambda: client.post(confirm_path, json={"offer_id": str(offer_a)}, headers=rider_headers),
                    lambda: client.post(confirm_path, json={"offer_id": str(offer_b)}, headers=rider_headers),
                )
                self.assertEqual(sorted([a.status_code, b.status_code]), [200, 409], (a.text, b.text))
                with Session(isolated) as db:
                    self.assertEqual(db.scalar(select(func.count()).select_from(RideBooking).where(RideBooking.request_id == ride_id)), 1)
                    self.assertEqual(db.scalar(select(func.count()).select_from(RideOffer).where(RideOffer.request_id == ride_id, RideOffer.status == "ACCEPTED")), 1)

                ride_id, offer_a, _ = seed()
                locations(ride_id)
                confirm_path = f"/rides/requests/{ride_id}/confirm"
                a, b = race(
                    lambda: client.post(confirm_path, json={"offer_id": str(offer_a)}, headers=rider_headers),
                    lambda: client.post(confirm_path, json={"offer_id": str(offer_a)}, headers=rider_headers),
                )
                self.assertEqual([a.status_code, b.status_code], [200, 200], (a.text, b.text))
                self.assertEqual(a.json()["booking"]["id"], b.json()["booking"]["id"])
                with Session(isolated) as db:
                    self.assertEqual(db.scalar(select(func.count()).select_from(Notification).where(
                        Notification.category == "ride", Notification.resource_id == ride_id,
                        Notification.event_type == "ride.booking_confirmed",
                    )), 1)
                    self.assertEqual(db.scalar(select(func.count()).select_from(Notification).where(
                        Notification.category == "ride", Notification.resource_id == ride_id,
                        Notification.event_type == "ride.offer_not_selected",
                    )), 1)

                ride_id, offer_a, _ = seed()
                locations(ride_id)
                a, b = race(
                    lambda: client.post(f"/rides/requests/{ride_id}/confirm", json={"offer_id": str(offer_a)}, headers=rider_headers),
                    lambda: client.post(f"/rides/requests/{ride_id}/offers/{offer_a}/withdraw", headers=driver_headers),
                )
                self.assertEqual(sorted([a.status_code, b.status_code]), [200, 409], (a.text, b.text))
                with Session(isolated) as db:
                    offer = db.get(RideOffer, offer_a)
                    bookings = db.scalar(select(func.count()).select_from(RideBooking).where(RideBooking.request_id == ride_id))
                    self.assertEqual((offer.status, bookings), ("ACCEPTED", 1) if a.status_code == 200 else ("WITHDRAWN", 0))
        finally:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
            engine.dispose()
