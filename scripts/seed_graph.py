"""Manual seed script for local Neo4j development."""

from app.config import configure_logging
from app.database import GraphDatabase_Connection
from app.queries import create_constraints, seed_sample_data


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
