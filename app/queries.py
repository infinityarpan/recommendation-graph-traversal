"""Cypher query operations for the travel recommendation service."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .database import get_session

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"viewed", "clicked", "added_to_cart", "booked", "abandoned"}
RECOMMENDATION_LIMIT = 10
MIN_SIMILARITY_SCORE = 2


def _validate_user_id(user_id: str) -> bool:
    """Return True when the provided user id is non-empty."""
    return bool(user_id and isinstance(user_id, str) and user_id.strip())


def _validate_action(action: str) -> bool:
    """Return True when the action is part of the supported clickstream vocabulary."""
    return action in VALID_ACTIONS


def recommend_similar(user_id: str, limit: int = 5) -> List[Dict]:
    """Return content-based recommendations from positive-intent travel actions."""
    if not _validate_user_id(user_id):
        raise ValueError("user_id must be a non-empty string")
    if not isinstance(limit, int) or limit < 1 or limit > RECOMMENDATION_LIMIT:
        raise ValueError(f"limit must be between 1 and {RECOMMENDATION_LIMIT}")

    def _recommend(tx, selected_user_id: str, selected_limit: int) -> List[Dict]:
        query = """
        MATCH (u:User {id: $user_id})-[seen:ACTION]->(p:Package)
        WHERE seen.type IN ['viewed', 'booked']
        WITH DISTINCT u, p
        MATCH (p)-[:SIMILAR_TO]->(rec:Package)
        WHERE NOT (u)-[:ACTION]->(rec)
        RETURN
            rec.id AS id,
            COALESCE(rec.name, rec.id) AS name,
            COALESCE(rec.price, 0) AS price,
            COALESCE(rec.category, 'unknown') AS category,
            COUNT(DISTINCT p) AS similarity_score
        ORDER BY similarity_score DESC, price ASC
        LIMIT $limit
        """
        result = tx.run(query, user_id=selected_user_id, limit=selected_limit)
        return [dict(record) for record in result]

    session = get_session()
    try:
        return session.execute_read(_recommend, user_id, limit)
    except Exception as exc:
        logger.error("Error fetching content-based recommendations: %s", exc)
        raise
    finally:
        session.close()


def ingest_clickstream_data(
    user_id: str,
    action: str,
    package_id: str,
    timestamp: Optional[str] = None,
) -> bool:
    """Upsert a clickstream ACTION relationship for a travel package."""
    if not _validate_user_id(user_id):
        raise ValueError("user_id must be a non-empty string")
    if not _validate_action(action):
        raise ValueError(f"action must be one of {VALID_ACTIONS}")
    if not package_id or not isinstance(package_id, str):
        raise ValueError("package_id must be a non-empty string")

    event_timestamp = timestamp or datetime.now().isoformat()

    def _process_click(tx) -> None:
        query = """
        MERGE (u:User {id: $user_id})
        MERGE (p:Package {id: $package_id})
        MERGE (u)-[r:ACTION {type: $action}]->(p)
        ON CREATE SET r.count = 1, r.first_action = $timestamp, r.last_action = $timestamp
        ON MATCH SET r.count = r.count + 1, r.last_action = $timestamp
        """
        tx.run(
            query,
            user_id=user_id,
            action=action,
            package_id=package_id,
            timestamp=event_timestamp,
        )

    session = get_session()
    try:
        session.execute_write(_process_click)
        return True
    except Exception as exc:
        logger.error("Error ingesting clickstream data: %s", exc)
        raise
    finally:
        session.close()


def collaborative_recommendations(user_id: str, limit: int = 5) -> List[Dict]:
    """Return recommendations based on overlapping travel-package behavior."""
    if not _validate_user_id(user_id):
        raise ValueError("user_id must be a non-empty string")
    if not isinstance(limit, int) or limit < 1 or limit > RECOMMENDATION_LIMIT:
        raise ValueError(f"limit must be between 1 and {RECOMMENDATION_LIMIT}")

    def _query(tx) -> List[Dict]:
        query = """
        MATCH (u:User {id: $user_id})-[r1:ACTION]->(p:Package)
        MATCH (other:User)-[r2:ACTION {type: r1.type}]->(p)
        WHERE other.id <> u.id
        WITH u, other, COUNT(DISTINCT p) AS common_count
        WHERE common_count >= $min_score
        MATCH (other)-[r3:ACTION]->(rec:Package)
        WHERE NOT (u)-[:ACTION]->(rec)
        RETURN
            rec.id AS id,
            COALESCE(rec.name, rec.id) AS name,
            COALESCE(rec.price, 0) AS price,
            COALESCE(rec.category, 'unknown') AS category,
            COUNT(DISTINCT other) AS similarity_score,
            SUM(r3.count) AS popularity_score
        ORDER BY similarity_score DESC, popularity_score DESC
        LIMIT $limit
        """
        result = tx.run(query, user_id=user_id, limit=limit, min_score=MIN_SIMILARITY_SCORE)
        return [dict(record) for record in result]

    session = get_session()
    try:
        return session.execute_read(_query)
    except Exception as exc:
        logger.error("Error fetching collaborative recommendations: %s", exc)
        raise
    finally:
        session.close()


def regional_recommendations(user_id: str, limit: int = 5) -> List[Dict]:
    """Return packages from destinations the user has already shown interest in."""
    if not _validate_user_id(user_id):
        raise ValueError("user_id must be a non-empty string")
    if not isinstance(limit, int) or limit < 1 or limit > RECOMMENDATION_LIMIT:
        raise ValueError(f"limit must be between 1 and {RECOMMENDATION_LIMIT}")

    def _query(tx) -> List[Dict]:
        query = """
        MATCH (u:User {id: $user_id})-[:ACTION]->(p:Package)
        MATCH (p)-[:LOCATED_IN]->(city:City)
        WITH DISTINCT u, city
        MATCH (city)<-[:LOCATED_IN]-(other_p:Package)
        WHERE NOT (u)-[:ACTION]->(other_p)
        RETURN
            other_p.id AS id,
            COALESCE(other_p.name, other_p.id) AS name,
            COALESCE(other_p.price, 0) AS price,
            COALESCE(other_p.category, 'unknown') AS category,
            city.name AS city,
            city.region AS region
        ORDER BY price ASC, id ASC
        LIMIT $limit
        """
        result = tx.run(query, user_id=user_id, limit=limit)
        return [dict(record) for record in result]

    session = get_session()
    try:
        return session.execute_read(_query)
    except Exception as exc:
        logger.error("Error fetching regional recommendations: %s", exc)
        raise
    finally:
        session.close()


def trending_recommendations(user_id: str, limit: int = 5) -> List[Dict]:
    """Return packages ranked by aggregate engagement across users."""
    if not _validate_user_id(user_id):
        raise ValueError("user_id must be a non-empty string")
    if not isinstance(limit, int) or limit < 1 or limit > RECOMMENDATION_LIMIT:
        raise ValueError(f"limit must be between 1 and {RECOMMENDATION_LIMIT}")

    def _query(tx) -> List[Dict]:
        query = """
        MATCH (p:Package)<-[r:ACTION]-(other:User)
        WHERE NOT EXISTS { MATCH (:User {id: $user_id})-[:ACTION]->(p) }
        WITH p,
             SUM(CASE WHEN r.type = 'booked' THEN r.count * 3 ELSE r.count END) AS engagement_score,
             COUNT(DISTINCT other) AS user_count
        RETURN
            p.id AS id,
            COALESCE(p.name, p.id) AS name,
            COALESCE(p.price, 0) AS price,
            COALESCE(p.category, 'unknown') AS category,
            engagement_score,
            user_count
        ORDER BY engagement_score DESC, user_count DESC, price ASC
        LIMIT $limit
        """
        result = tx.run(query, user_id=user_id, limit=limit)
        return [dict(record) for record in result]

    session = get_session()
    try:
        return session.execute_read(_query)
    except Exception as exc:
        logger.error("Error fetching trending recommendations: %s", exc)
        raise
    finally:
        session.close()


def get_user_stats(user_id: str) -> Optional[Dict]:
    """Return aggregate engagement statistics for a user."""
    if not _validate_user_id(user_id):
        raise ValueError("user_id must be a non-empty string")

    def _query(tx) -> Optional[Dict]:
        query = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[r:ACTION]->(p:Package)
        RETURN
            u.id AS user_id,
            COALESCE(SUM(r.count), 0) AS total_actions,
            COALESCE(SUM(CASE WHEN r.type = 'viewed' THEN r.count ELSE 0 END), 0) AS views,
            COALESCE(SUM(CASE WHEN r.type = 'clicked' THEN r.count ELSE 0 END), 0) AS clicks,
            COALESCE(SUM(CASE WHEN r.type = 'added_to_cart' THEN r.count ELSE 0 END), 0) AS added_to_cart,
            COALESCE(SUM(CASE WHEN r.type = 'booked' THEN r.count ELSE 0 END), 0) AS bookings,
            COALESCE(SUM(CASE WHEN r.type = 'abandoned' THEN r.count ELSE 0 END), 0) AS abandoned,
            COUNT(DISTINCT p) AS unique_packages
        """
        result = tx.run(query, user_id=user_id)
        records = [dict(record) for record in result]
        return records[0] if records else None

    session = get_session()
    try:
        return session.execute_read(_query)
    except Exception as exc:
        logger.error("Error fetching user stats: %s", exc)
        raise
    finally:
        session.close()
