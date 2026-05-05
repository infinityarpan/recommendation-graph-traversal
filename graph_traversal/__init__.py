"""Travel recommendation service backed by Neo4j."""

__version__ = "3.0.0"

from .database import GraphDatabase_Connection
from .queries import (
    collaborative_recommendations,
    create_constraints,
    get_user_stats,
    ingest_clickstream_data,
    recommend_similar,
    regional_recommendations,
    seed_sample_data,
    trending_recommendations,
)

try:  # FastAPI is an application dependency, but query helpers stay importable without it.
    from .api import app, create_app
except ImportError:  # pragma: no cover - used only before app dependencies are installed.
    app = None
    create_app = None

__all__ = [
    "app",
    "create_app",
    "GraphDatabase_Connection",
    "create_constraints",
    "seed_sample_data",
    "recommend_similar",
    "collaborative_recommendations",
    "regional_recommendations",
    "trending_recommendations",
    "ingest_clickstream_data",
    "get_user_stats",
]
