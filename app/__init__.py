"""Travel recommendation service backed by Neo4j."""

__version__ = "3.0.0"

from .database import GraphDatabase_Connection
from .queries import (
    collaborative_recommendations,
    get_user_stats,
    ingest_clickstream_data,
    recommend_similar,
    regional_recommendations,
    trending_recommendations,
)

try:  # FastAPI is an application dependency, but query helpers stay importable without it.
    from .main import app, create_app
except ImportError:  # pragma: no cover - used only before app dependencies are installed.
    app = None
    create_app = None

__all__ = [
    "app",
    "create_app",
    "GraphDatabase_Connection",
    "recommend_similar",
    "collaborative_recommendations",
    "regional_recommendations",
    "trending_recommendations",
    "ingest_clickstream_data",
    "get_user_stats",
]
