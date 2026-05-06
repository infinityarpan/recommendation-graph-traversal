import unittest
from unittest.mock import patch

from tests.helpers import FakeSession

import app.queries as queries


class QueryBehaviorTests(unittest.TestCase):
    def test_recommend_similar_only_uses_positive_actions(self):
        session = FakeSession(records=[{"id": "pkg1"}])

        with patch("app.queries.get_session", return_value=session):
            queries.recommend_similar("u1", limit=3)

        query, params = session.tx.calls[0]
        self.assertIn("WHERE seen.type IN ['viewed', 'booked']", query)
        self.assertIn("WITH DISTINCT u, p", query)
        self.assertIn("COUNT(DISTINCT p) AS similarity_score", query)
        self.assertIn("COALESCE(rec.category, 'unknown') AS category", query)
        self.assertIn("ORDER BY similarity_score DESC, price ASC", query)
        self.assertEqual(params["user_id"], "u1")
        self.assertEqual(params["limit"], 3)

    def test_collaborative_recommendations_counts_distinct_packages(self):
        session = FakeSession(records=[{"id": "pkg1"}])

        with patch("app.queries.get_session", return_value=session):
            queries.collaborative_recommendations("u1", limit=2)

        query, _ = session.tx.calls[0]
        self.assertIn("COUNT(DISTINCT p) AS common_count", query)

    def test_regional_recommendations_return_distinct_packages(self):
        session = FakeSession(records=[{"id": "pkg1"}])

        with patch("app.queries.get_session", return_value=session):
            queries.regional_recommendations("u1", limit=2)

        query, _ = session.tx.calls[0]
        self.assertIn("WITH DISTINCT u, city", query)
        self.assertIn("ORDER BY price ASC, id ASC", query)

    def test_trending_recommendations_are_deterministically_ordered(self):
        session = FakeSession(records=[{"id": "pkg1"}])

        with patch("app.queries.get_session", return_value=session):
            queries.trending_recommendations("u1", limit=2)

        query, _ = session.tx.calls[0]
        self.assertIn("ORDER BY engagement_score DESC, user_count DESC, price ASC", query)
        self.assertIn("WHERE NOT EXISTS { MATCH (:User {id: $user_id})-[:ACTION]->(p) }", query)
        self.assertIn("COALESCE(p.category, 'unknown') AS category", query)

    def test_database_errors_are_propagated_from_read_queries(self):
        session = FakeSession(error=RuntimeError("neo4j unavailable"))

        with patch("app.queries.get_session", return_value=session):
            with self.assertRaises(RuntimeError):
                queries.recommend_similar("u1")

        self.assertTrue(session.closed)

    def test_database_errors_are_propagated_from_write_queries(self):
        session = FakeSession(error=RuntimeError("neo4j unavailable"))

        with patch("app.queries.get_session", return_value=session):
            with self.assertRaises(RuntimeError):
                queries.ingest_clickstream_data("u1", "viewed", "pkg1")

        self.assertTrue(session.closed)


if __name__ == "__main__":
    unittest.main()
