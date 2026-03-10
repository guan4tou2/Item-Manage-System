"""健康檢查路由測試"""
import unittest
from unittest.mock import patch

import tests.conftest  # noqa: F401

from app import create_app


class HealthRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch("app.health.routes.cache.get", return_value="ok")
    @patch("app.health.routes.cache.set")
    @patch("app.health.routes.db.session.execute")
    def test_ready_returns_200_when_dependencies_pass(
        self,
        mock_execute,
        _mock_cache_set,
        _mock_cache_get,
    ):
        mock_execute.return_value.scalar.return_value = 1

        response = self.client.get("/ready")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["ready"])
        self.assertEqual(data["checks"]["database"], "pass")
        self.assertEqual(data["checks"]["cache"], "pass")

    @patch("app.health.routes.cache.set", side_effect=RuntimeError("cache down"))
    @patch("app.health.routes.db.session.execute")
    def test_ready_returns_503_when_cache_fails(
        self,
        mock_execute,
        _mock_cache_set,
    ):
        mock_execute.return_value.scalar.return_value = 1

        response = self.client.get("/ready")
        data = response.get_json()

        self.assertEqual(response.status_code, 503)
        self.assertFalse(data["ready"])
        self.assertIn("error:", data["checks"]["cache"])
