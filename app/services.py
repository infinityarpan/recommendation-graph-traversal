"""Thin service layer used by the FastAPI application."""

from typing import Dict, List, Optional

from .database import GraphDatabase_Connection
from .queries import (
    collaborative_recommendations,
    get_user_stats,
    recommend_similar,
    regional_recommendations,
    trending_recommendations,
)


def get_health_status() -> Dict[str, str]:
    """Return a lightweight readiness payload."""
    GraphDatabase_Connection.get_driver()
    return {"status": "ok"}


def get_similar_recommendations(user_id: str, limit: int) -> List[Dict]:
    return recommend_similar(user_id, limit=limit)


def get_collaborative_recommendations(user_id: str, limit: int) -> List[Dict]:
    return collaborative_recommendations(user_id, limit=limit)


def get_regional_recommendations(user_id: str, limit: int) -> List[Dict]:
    return regional_recommendations(user_id, limit=limit)


def get_trending_recommendations(user_id: str, limit: int) -> List[Dict]:
    return trending_recommendations(user_id, limit=limit)


def fetch_user_stats(user_id: str) -> Optional[Dict]:
    return get_user_stats(user_id)
