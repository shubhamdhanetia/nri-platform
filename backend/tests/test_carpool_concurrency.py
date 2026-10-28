import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.api.carpools import router
from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.dependencies import get_db
from app.models.carpool import CarpoolSeatRequest, CarpoolTrip
from app.models.notification import Notification
from app.models.ride import DriverProfile
from app.models.user import User
import app.models.saved_post
from test_rides import place


@unittest.skipUnless(os.getenv("RIDE_TEST_POSTGRES") == "1", "Set RIDE_TEST_POSTGRES=1 for isolated PostgreSQL concurrency tests")
class CarpoolConcurrencyTests(unittest.TestCase):
    def test_capacity_duplicates_and_cancellation_races(self):
        engine = create_engine(settings.DATABASE_URL)
        self.assertEqual(engine.dialect.name, "postgresql")
        schema = "carpool_test_" + uuid4().hex
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        isolated = engine.execution_options(schema_translate_map={None: schema})
        try:
            Base.metadata.create_all(isolated)
            app = FastAPI()
            app.include_router(router, prefix="/rides/carpools")

            def test_db():
                with Session(isolated, autoflush=False) as db:
                    yield db

            app.dependency_overrides[get_db] = test_db
            with Session(isolated) as db:
                for user_id in (1, 2, 3):
                    db.add(User(id=user_id, name=f"Member {user_id}", email=f"{user_id}@example.test", provider="test", provider_id=str(user_id)))
                db.commit()
                db.add(DriverProfile(user_id=1, vehicle="Test car", passenger_capacity=3, phone="+14155550101", acknowledgement_at=datetime.now(timezone.utc).replace(tzinfo=None)))
                db.commit()

            def seed():
                with Session(isolated) as db:
                    start = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
                    trip = CarpoolTrip(
                        driver_id=1, pickup=place("pickup").model_dump(), dropoff=place("dropoff").model_dump(),
                        pickup_start=start, pickup_end=start + timedelta(minutes=30), timezone="UTC",
                        seats=1, bags_per_person=1, amount=40, currency="USD", vehicle="Test car", notes="",
                    )
                    db.add(trip)
                    db.flush()
                    requests = [CarpoolSeatRequest(
                        trip_id=trip.id, rider_id=rider_id, passengers=1, bags=0, message="", rider_phone=f"+1415555010{rider_id}",
                    ) for rider_id in (2, 3)]
                    db.add_all(requests)
                    db.commit()
                    return trip.id, requests[0].id, requests[1].id

            def headers(user_id):
                return {"Authorization": f"Bearer {create_access_token(user_id)}"}

            def race(first, second):
                barrier = Barrier(2)

                def run(call):
                    barrier.wait(timeout=10)
                    return call()

                with ThreadPoolExecutor(max_workers=2) as executor:
                    a = executor.submit(run, first)
                    b = executor.submit(run, second)
                    return a.result(timeout=20), b.result(timeout=20)

            with TestClient(app) as client:
                def accept(trip_id, request_id):
                    return client.post(f"/rides/carpools/trips/{trip_id}/requests/{request_id}/accept", headers=headers(1))

                trip_id, first, second = seed()
                a, b = race(lambda: accept(trip_id, first), lambda: accept(trip_id, second))
                self.assertEqual(sorted([a.status_code, b.status_code]), [200, 409], (a.text, b.text))
                with Session(isolated) as db:
                    self.assertEqual(db.scalar(select(func.sum(CarpoolSeatRequest.passengers)).where(
                        CarpoolSeatRequest.trip_id == trip_id, CarpoolSeatRequest.status == "CONFIRMED",
                    )), 1)

                trip_id, first, _ = seed()
                a, b = race(lambda: accept(trip_id, first), lambda: accept(trip_id, first))
                self.assertEqual([a.status_code, b.status_code], [200, 200], (a.text, b.text))
                with Session(isolated) as db:
                    self.assertEqual(db.scalar(select(func.count()).select_from(Notification).where(
                        Notification.category == "carpool", Notification.resource_id == trip_id,
                    )), 1)

                trip_id, first, _ = seed()
                a, b = race(
                    lambda: accept(trip_id, first),
                    lambda: client.post(f"/rides/carpools/trips/{trip_id}/requests/{first}/cancel", headers=headers(2), json={"reason": "Changed plans"}),
                )
                self.assertEqual(b.status_code, 200, b.text)
                self.assertIn(a.status_code, (200, 409), a.text)
                with Session(isolated) as db:
                    self.assertEqual(db.get(CarpoolSeatRequest, first).status, "CANCELLED")

                trip_id, first, _ = seed()
                a, b = race(
                    lambda: accept(trip_id, first),
                    lambda: client.post(f"/rides/carpools/trips/{trip_id}/cancel", headers=headers(1), json={"reason": "Car unavailable"}),
                )
                self.assertEqual(b.status_code, 200, b.text)
                self.assertIn(a.status_code, (200, 409), a.text)
                with Session(isolated) as db:
                    self.assertEqual(db.get(CarpoolTrip, trip_id).status, "CANCELLED")
                    self.assertEqual(db.get(CarpoolSeatRequest, first).status, "CANCELLED")

                trip_id, _, _ = seed()
                with Session(isolated) as db:
                    db.query(CarpoolSeatRequest).filter(CarpoolSeatRequest.trip_id == trip_id).delete()
                    db.commit()

                def request():
                    return client.post(f"/rides/carpools/trips/{trip_id}/requests", headers=headers(2), json={
                        "passengers": 1, "bags": 0, "rider_phone": "+14155550102",
                    })

                a, b = race(request, request)
                self.assertEqual(sorted([a.status_code, b.status_code]), [201, 409], (a.text, b.text))
        finally:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
            engine.dispose()
