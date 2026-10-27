import unittest
from copy import deepcopy
from unittest.mock import patch

import h3
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.locations import router
from app.schemas.location import LocationDetailsRequest
from app.services.location_search import resolve_post_location


class LocationDetailsTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "status": "success",
            "data": {
                "addressComponents": {
                    "CITY": "Fremont",
                    "COUNTRY_CODE": "US",
                    "FIRST_LEVEL_SUBDIVISION_CODE": "CA",
                    "POSTAL_CODE": "94538",
                    "STREET_NAME": "Sample Street",
                },
                "addressLine1": "Sample meeting point",
                "addressLine2": "Fremont, CA",
                "categories": [],
                "fullAddress": "Sample meeting point, Fremont, CA",
                "id": "sample-location",
                "lat": 37.55,
                "long": -121.98,
                "provider": "uber_places",
                "title": "Sample meeting point",
                "type": "pickup",
            },
        }
        app = FastAPI()
        app.include_router(router, prefix="/locations")
        app.dependency_overrides[get_current_user] = lambda: object()
        self.client = TestClient(app)
        self.provider = patch("app.services.location_search._post_to_uber", return_value=self.payload)
        self.mock_provider = self.provider.start()
        self.addCleanup(self.provider.stop)
        self.addCleanup(self.client.close)

    def test_details_accepts_missing_null_and_present_house_number(self):
        for value in ("missing", None, "123"):
            with self.subTest(house_number=value):
                components = self.payload["data"]["addressComponents"]
                components.pop("HOUSE_NUMBER", None)
                if value != "missing":
                    components["HOUSE_NUMBER"] = value
                response = self.client.post("/locations/details", json={"id": "sample-location"})
                self.assertEqual(response.status_code, 200, response.text)
                data = response.json()["data"]
                self.assertEqual(data["addressComponents"]["HOUSE_NUMBER"], None if value == "missing" else value)
                self.assertEqual(data["lat"], 37.55)
                self.assertEqual(data["fullAddress"], self.payload["data"]["fullAddress"])

    def test_post_and_ride_location_resolution_without_house_number(self):
        location = resolve_post_location("sample-location")
        self.assertEqual(location.location_id, "sample-location")
        self.assertEqual(location.city, "Fremont")
        self.assertEqual(location.h3_cell_id, h3.latlng_to_cell(37.55, -121.98, 8))
        self.assertEqual(self.mock_provider.call_args.args[1], LocationDetailsRequest(id="sample-location").model_dump())

    def test_invalid_provider_responses_still_return_502(self):
        for field in ("lat", "fullAddress", "id"):
            with self.subTest(missing_field=field):
                payload = deepcopy(self.payload)
                del payload["data"][field]
                self.mock_provider.return_value = payload
                response = self.client.post("/locations/details", json={"id": "sample-location"})
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.json()["detail"], "Location provider returned an invalid response")
