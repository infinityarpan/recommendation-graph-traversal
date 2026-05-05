import unittest
from unittest.mock import patch

from tests.helpers import FakeSession

import graph_traversal.queries as queries


class QueryBehaviorTests(unittest.TestCase):
    def test_create_constraints_runs_expected_statements(self):
        session = FakeSession()

        with patch("graph_traversal.queries.get_session", return_value=session):
            queries.create_constraints()

        self.assertTrue(session.closed)
        statements = [query for query, _ in session.tx.calls]
        self.assertEqual(len(statements), 3)
        self.assertTrue(any("user_id_unique" in statement for statement in statements))
        self.assertTrue(any("package_id_unique" in statement for statement in statements))
        self.assertTrue(any("city_name_region_unique" in statement for statement in statements))

    def test_seed_sample_data_merges_packages_by_id_only(self):
        session = FakeSession()

        with patch("graph_traversal.queries.get_session", return_value=session):
            queries.seed_sample_data()

        self.assertTrue(session.closed)
        combined_query = "\n".join(query for query, _ in session.tx.calls)
        self.assertIn('MERGE (p1:Package {id: "pkg_goa_beach_escape"})', combined_query)
        self.assertIn("SET p1.name =", combined_query)
        self.assertNotIn('MERGE (p1:Package {id: "pkg_goa_beach_escape", name:', combined_query)

    def test_seed_sample_data_uses_standard_action_schema(self):
        session = FakeSession()

        with patch("graph_traversal.queries.get_session", return_value=session):
            queries.seed_sample_data()

        combined_query = "\n".join(query for query, _ in session.tx.calls)
        self.assertIn('ACTION {type: "added_to_cart"}', combined_query)
        self.assertIn('ACTION {type: "abandoned"}', combined_query)
        self.assertIn("ON CREATE SET a1.count = 4", combined_query)
        self.assertNotIn("\n            SET a1.count = 4", combined_query)

    def test_recommend_similar_only_uses_positive_actions(self):
        session = FakeSession(records=[{"id": "pkg1"}])

        with patch("graph_traversal.queries.get_session", return_value=session):
            queries.recommend_similar("u1", limit=3)

        query, params = session.tx.calls[0]
        self.assertIn("WHERE seen.type IN ['viewed', 'booked']", query)
        self.assertIn("WITH u, COLLECT(DISTINCT p) AS source_packages", query)
        self.assertIn("COUNT(DISTINCT p) AS similarity_score", query)
        self.assertIn("COALESCE(rec.category, 'unknown') AS category", query)
        self.assertIn("ORDER BY similarity_score DESC, price ASC", query)
        self.assertEqual(params["user_id"], "u1")
        self.assertEqual(params["limit"], 3)

    def test_collaborative_recommendations_counts_distinct_packages(self):
        session = FakeSession(records=[{"id": "pkg1"}])

        with patch("graph_traversal.queries.get_session", return_value=session):
            queries.collaborative_recommendations("u1", limit=2)

        query, _ = session.tx.calls[0]
        self.assertIn("COUNT(DISTINCT p) AS common_count", query)

    def test_regional_recommendations_return_distinct_packages(self):
        session = FakeSession(records=[{"id": "pkg1"}])

        with patch("graph_traversal.queries.get_session", return_value=session):
            queries.regional_recommendations("u1", limit=2)

        query, _ = session.tx.calls[0]
        self.assertIn("RETURN DISTINCT", query)
        self.assertIn("ORDER BY price ASC", query)

    def test_trending_recommendations_are_deterministically_ordered(self):
        session = FakeSession(records=[{"id": "pkg1"}])

        with patch("graph_traversal.queries.get_session", return_value=session):
            queries.trending_recommendations("u1", limit=2)

        query, _ = session.tx.calls[0]
        self.assertIn("ORDER BY engagement_score DESC, user_count DESC, price ASC", query)
        self.assertIn("COALESCE(p.category, 'unknown') AS category", query)

    def test_database_errors_are_propagated_from_read_queries(self):
        session = FakeSession(error=RuntimeError("neo4j unavailable"))

        with patch("graph_traversal.queries.get_session", return_value=session):
            with self.assertRaises(RuntimeError):
                queries.recommend_similar("u1")

        self.assertTrue(session.closed)

    def test_database_errors_are_propagated_from_write_queries(self):
        session = FakeSession(error=RuntimeError("neo4j unavailable"))

        with patch("graph_traversal.queries.get_session", return_value=session):
            with self.assertRaises(RuntimeError):
                queries.ingest_clickstream_data("u1", "viewed", "pkg1")

        self.assertTrue(session.closed)


if __name__ == "__main__":
    unittest.main()
