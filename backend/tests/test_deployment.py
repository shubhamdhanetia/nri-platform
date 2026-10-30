import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app


class DeploymentTests(unittest.TestCase):
    def test_settings_accept_json_cors_origins(self):
        with patch.dict("os.environ", {
            "CORS_ORIGINS": '["https://client-bay-alpha-95.vercel.app"]',
        }):
            settings = Settings(
                _env_file=None,
                GOOGLE_CLIENT_ID="test",
                JWT_SECRET="test",
                DATABASE_URL="sqlite://",
            )
        self.assertEqual(settings.CORS_ORIGINS, ["https://client-bay-alpha-95.vercel.app"])

    def test_health_is_public_and_does_not_require_database(self):
        with TestClient(app) as client:
            response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_cors_allows_configured_origin_and_rejects_other_origins(self):
        from app.core.config import settings

        with TestClient(app) as client:
            for origin, expected in (
                (settings.CORS_ORIGINS[0], 200),
                ("https://untrusted.example", 400),
            ):
                response = client.options(
                    "/users/me",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "authorization",
                    },
                )
                self.assertEqual(response.status_code, expected)
                if expected == 200:
                    self.assertEqual(response.headers["access-control-allow-origin"], origin)
                else:
                    self.assertNotIn("access-control-allow-origin", response.headers)
