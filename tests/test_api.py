import unittest
from unittest.mock import patch

from tests.helpers import dotenv_stub, neo4j_stub  # noqa: F401

try:
    from fastapi.testclient import TestClient
    from graph_traversal.api import create_app

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@unittest.skipUnless(HAS_FASTAPI, "FastAPI test dependencies are not installed")
class ApiBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.initialize = patch("graph_traversal.api.GraphDatabase_Connection.initialize")
        self.close = patch("graph_traversal.api.GraphDatabase_Connection.close")
        self.initialize.start()
        self.close.start()
        self.client = TestClient(create_app())

    def tearDown(self):
        self.initialize.stop()
        self.close.stop()

    def test_health_endpoint_returns_success(self):
        with patch("graph_traversal.routes.get_health_status", return_value={"status": "ok"}):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_similar_endpoint_returns_recommendations(self):
        payload = [
            {"id": "pkg1", "name": "Goa", "price": 10000, "category": "beach", "similarity_score": 2}
        ]
        with patch("graph_traversal.routes.get_similar_recommendations", return_value=payload):
            response = self.client.get("/users/u1/recommendations/similar?limit=3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], "u1")
        self.assertEqual(response.json()["limit"], 3)
        self.assertEqual(len(response.json()["recommendations"]), 1)

    def test_invalid_limit_returns_422(self):
        response = self.client.get("/users/u1/recommendations/trending?limit=0")
        self.assertEqual(response.status_code, 422)

    def test_runtime_errors_translate_to_503(self):
        with patch("graph_traversal.routes.get_trending_recommendations", side_effect=RuntimeError("db down")):
            response = self.client.get("/users/u1/recommendations/trending")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Neo4j service unavailable")

    def test_missing_user_stats_returns_404(self):
        with patch("graph_traversal.routes.fetch_user_stats", return_value=None):
            response = self.client.get("/users/u9/stats")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
