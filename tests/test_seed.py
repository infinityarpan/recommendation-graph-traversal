import unittest
from unittest.mock import patch

from tests.helpers import FakeSession

import bootstrap.seed as seed


class SeedBehaviorTests(unittest.TestCase):
    def test_create_constraints_runs_expected_statements(self):
        session = FakeSession()

        with patch("bootstrap.seed.get_session", return_value=session):
            seed.create_constraints()

        self.assertTrue(session.closed)
        statements = [query for query, _ in session.tx.calls]
        self.assertEqual(len(statements), 3)
        self.assertTrue(any("user_id_unique" in statement for statement in statements))
        self.assertTrue(any("package_id_unique" in statement for statement in statements))
        self.assertTrue(any("city_name_region_unique" in statement for statement in statements))

    def test_seed_sample_data_merges_packages_by_id_only(self):
        session = FakeSession()

        with patch("bootstrap.seed.get_session", return_value=session):
            seed.seed_sample_data()

        self.assertTrue(session.closed)
        combined_query = "\n".join(query for query, _ in session.tx.calls)
        self.assertIn('MERGE (p1:Package {id: "pkg_goa_beach_escape"})', combined_query)
        self.assertIn("SET p1.name =", combined_query)
        self.assertNotIn('MERGE (p1:Package {id: "pkg_goa_beach_escape", name:', combined_query)

    def test_seed_sample_data_uses_standard_action_schema(self):
        session = FakeSession()

        with patch("bootstrap.seed.get_session", return_value=session):
            seed.seed_sample_data()

        combined_query = "\n".join(query for query, _ in session.tx.calls)
        self.assertIn('ACTION {type: "added_to_cart"}', combined_query)
        self.assertIn('ACTION {type: "abandoned"}', combined_query)
        self.assertIn("ON CREATE SET a1.count = 4", combined_query)
        self.assertNotIn("\n            SET a1.count = 4", combined_query)


if __name__ == "__main__":
    unittest.main()
