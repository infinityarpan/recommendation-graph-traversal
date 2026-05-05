"""Manual seed script for local Neo4j development."""

from graph_traversal.config import configure_logging
from graph_traversal.database import GraphDatabase_Connection
from graph_traversal.queries import create_constraints, seed_sample_data


def main() -> None:
    configure_logging()
    GraphDatabase_Connection.initialize()
    try:
        create_constraints()
        seed_sample_data()
    finally:
        GraphDatabase_Connection.close()


if __name__ == "__main__":
    main()
