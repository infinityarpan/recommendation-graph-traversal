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


def create_constraints() -> None:
    """Create graph constraints used by the recommendation service."""

    statements = [
        "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
        "CREATE CONSTRAINT package_id_unique IF NOT EXISTS FOR (p:Package) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT city_name_region_unique IF NOT EXISTS FOR (c:City) REQUIRE (c.name, c.region) IS UNIQUE",
    ]

    def _create(tx) -> None:
        for statement in statements:
            tx.run(statement)

    session = get_session()
    try:
        session.execute_write(_create)
        logger.info("Graph constraints created successfully")
    except Exception as exc:
        logger.error("Error creating graph constraints: %s", exc)
        raise
    finally:
        session.close()


def seed_sample_data() -> None:
    """Seed a compact, repeatable travel catalog and sample clickstream graph.

    The seed is additive and non-destructive:
    - users are merged by ``id``
    - packages are merged by ``id`` and mutable fields are set separately
    - cities are merged by ``(name, region)``
    - seeded ACTION relationships only initialize counts when first created
    """

    def _seed(tx) -> None:
        tx.run(
            """
            MERGE (u1:User {id: "u1"})
            SET u1.name = "Arpan", u1.created_at = COALESCE(u1.created_at, datetime())

            MERGE (u2:User {id: "u2"})
            SET u2.name = "Priya", u2.created_at = COALESCE(u2.created_at, datetime())

            MERGE (u3:User {id: "u3"})
            SET u3.name = "Rohan", u3.created_at = COALESCE(u3.created_at, datetime())

            MERGE (u4:User {id: "u4"})
            SET u4.name = "Nisha", u4.created_at = COALESCE(u4.created_at, datetime())

            MERGE (goa:City {name: "Goa", region: "West"})
            MERGE (jaipur:City {name: "Jaipur", region: "North"})
            MERGE (kerala:City {name: "Alleppey", region: "South"})
            MERGE (leh:City {name: "Leh", region: "North"})
            MERGE (mumbai:City {name: "Mumbai", region: "West"})
            """
        )

        tx.run(
            """
            MERGE (p1:Package {id: "pkg_goa_beach_escape"})
            SET p1.name = "Goa Beach Escape",
                p1.price = 15000,
                p1.duration = 5,
                p1.category = "beach"

            MERGE (p2:Package {id: "pkg_goa_water_sports"})
            SET p2.name = "Goa Water Sports Adventure",
                p2.price = 18500,
                p2.duration = 6,
                p2.category = "adventure"

            MERGE (p3:Package {id: "pkg_kerala_backwaters"})
            SET p3.name = "Kerala Backwater Cruise",
                p3.price = 14500,
                p3.duration = 4,
                p3.category = "nature"

            MERGE (p4:Package {id: "pkg_jaipur_palaces"})
            SET p4.name = "Jaipur Palace Trail",
                p4.price = 13200,
                p4.duration = 3,
                p4.category = "culture"

            MERGE (p5:Package {id: "pkg_leh_roadtrip"})
            SET p5.name = "Leh High-Altitude Roadtrip",
                p5.price = 26800,
                p5.duration = 7,
                p5.category = "adventure"

            MERGE (p6:Package {id: "pkg_mumbai_weekender"})
            SET p6.name = "Mumbai Culture Weekender",
                p6.price = 11200,
                p6.duration = 2,
                p6.category = "city"
            """
        )

        tx.run(
            """
            MATCH (p1:Package {id: "pkg_goa_beach_escape"}), (goa:City {name: "Goa", region: "West"})
            MERGE (p1)-[:LOCATED_IN]->(goa)

            MATCH (p2:Package {id: "pkg_goa_water_sports"}), (goa:City {name: "Goa", region: "West"})
            MERGE (p2)-[:LOCATED_IN]->(goa)

            MATCH (p3:Package {id: "pkg_kerala_backwaters"}), (kerala:City {name: "Alleppey", region: "South"})
            MERGE (p3)-[:LOCATED_IN]->(kerala)

            MATCH (p4:Package {id: "pkg_jaipur_palaces"}), (jaipur:City {name: "Jaipur", region: "North"})
            MERGE (p4)-[:LOCATED_IN]->(jaipur)

            MATCH (p5:Package {id: "pkg_leh_roadtrip"}), (leh:City {name: "Leh", region: "North"})
            MERGE (p5)-[:LOCATED_IN]->(leh)

            MATCH (p6:Package {id: "pkg_mumbai_weekender"}), (mumbai:City {name: "Mumbai", region: "West"})
            MERGE (p6)-[:LOCATED_IN]->(mumbai)
            """
        )

        tx.run(
            """
            MATCH (p1:Package {id: "pkg_goa_beach_escape"}), (p2:Package {id: "pkg_goa_water_sports"})
            MERGE (p1)-[:SIMILAR_TO {reason: "same_destination"}]->(p2)
            MERGE (p2)-[:SIMILAR_TO {reason: "same_destination"}]->(p1)

            MATCH (p2:Package {id: "pkg_goa_water_sports"}), (p5:Package {id: "pkg_leh_roadtrip"})
            MERGE (p2)-[:SIMILAR_TO {reason: "adventure_travel"}]->(p5)
            MERGE (p5)-[:SIMILAR_TO {reason: "adventure_travel"}]->(p2)

            MATCH (p3:Package {id: "pkg_kerala_backwaters"}), (p1:Package {id: "pkg_goa_beach_escape"})
            MERGE (p3)-[:SIMILAR_TO {reason: "leisure_getaway"}]->(p1)

            MATCH (p4:Package {id: "pkg_jaipur_palaces"}), (p6:Package {id: "pkg_mumbai_weekender"})
            MERGE (p4)-[:SIMILAR_TO {reason: "urban_culture"}]->(p6)
            """
        )

        tx.run(
            """
            MATCH (u1:User {id: "u1"}), (p1:Package {id: "pkg_goa_beach_escape"})
            MERGE (u1)-[a1:ACTION {type: "viewed"}]->(p1)
            ON CREATE SET a1.count = 4, a1.first_action = datetime(), a1.last_action = datetime()

            MATCH (u1:User {id: "u1"}), (p1:Package {id: "pkg_goa_beach_escape"})
            MERGE (u1)-[a2:ACTION {type: "clicked"}]->(p1)
            ON CREATE SET a2.count = 2, a2.first_action = datetime(), a2.last_action = datetime()

            MATCH (u1:User {id: "u1"}), (p2:Package {id: "pkg_goa_water_sports"})
            MERGE (u1)-[a3:ACTION {type: "added_to_cart"}]->(p2)
            ON CREATE SET a3.count = 1, a3.first_action = datetime(), a3.last_action = datetime()

            MATCH (u1:User {id: "u1"}), (p2:Package {id: "pkg_goa_water_sports"})
            MERGE (u1)-[a4:ACTION {type: "abandoned"}]->(p2)
            ON CREATE SET a4.count = 1, a4.first_action = datetime(), a4.last_action = datetime()

            MATCH (u2:User {id: "u2"}), (p3:Package {id: "pkg_kerala_backwaters"})
            MERGE (u2)-[a5:ACTION {type: "viewed"}]->(p3)
            ON CREATE SET a5.count = 3, a5.first_action = datetime(), a5.last_action = datetime()

            MATCH (u2:User {id: "u2"}), (p3:Package {id: "pkg_kerala_backwaters"})
            MERGE (u2)-[a6:ACTION {type: "clicked"}]->(p3)
            ON CREATE SET a6.count = 1, a6.first_action = datetime(), a6.last_action = datetime()

            MATCH (u2:User {id: "u2"}), (p3:Package {id: "pkg_kerala_backwaters"})
            MERGE (u2)-[a7:ACTION {type: "booked"}]->(p3)
            ON CREATE SET a7.count = 1, a7.first_action = datetime(), a7.last_action = datetime()

            MATCH (u2:User {id: "u2"}), (p1:Package {id: "pkg_goa_beach_escape"})
            MERGE (u2)-[a8:ACTION {type: "viewed"}]->(p1)
            ON CREATE SET a8.count = 1, a8.first_action = datetime(), a8.last_action = datetime()

            MATCH (u3:User {id: "u3"}), (p4:Package {id: "pkg_jaipur_palaces"})
            MERGE (u3)-[a9:ACTION {type: "viewed"}]->(p4)
            ON CREATE SET a9.count = 2, a9.first_action = datetime(), a9.last_action = datetime()

            MATCH (u3:User {id: "u3"}), (p4:Package {id: "pkg_jaipur_palaces"})
            MERGE (u3)-[a10:ACTION {type: "clicked"}]->(p4)
            ON CREATE SET a10.count = 1, a10.first_action = datetime(), a10.last_action = datetime()

            MATCH (u3:User {id: "u3"}), (p6:Package {id: "pkg_mumbai_weekender"})
            MERGE (u3)-[a11:ACTION {type: "viewed"}]->(p6)
            ON CREATE SET a11.count = 1, a11.first_action = datetime(), a11.last_action = datetime()

            MATCH (u4:User {id: "u4"}), (p5:Package {id: "pkg_leh_roadtrip"})
            MERGE (u4)-[a12:ACTION {type: "viewed"}]->(p5)
            ON CREATE SET a12.count = 3, a12.first_action = datetime(), a12.last_action = datetime()

            MATCH (u4:User {id: "u4"}), (p5:Package {id: "pkg_leh_roadtrip"})
            MERGE (u4)-[a13:ACTION {type: "clicked"}]->(p5)
            ON CREATE SET a13.count = 2, a13.first_action = datetime(), a13.last_action = datetime()

            MATCH (u4:User {id: "u4"}), (p5:Package {id: "pkg_leh_roadtrip"})
            MERGE (u4)-[a14:ACTION {type: "booked"}]->(p5)
            ON CREATE SET a14.count = 1, a14.first_action = datetime(), a14.last_action = datetime()
            """
        )

    session = get_session()
    try:
        session.execute_write(_seed)
        logger.info("Sample travel data seeded successfully")
    except Exception as exc:
        logger.error("Error seeding sample travel data: %s", exc)
        raise
    finally:
        session.close()


def create_initial_data() -> None:
    """Backward-compatible alias for seed_sample_data()."""
    seed_sample_data()


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
        WITH u, COLLECT(DISTINCT p) AS source_packages
        UNWIND source_packages AS p
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
        MATCH (city)<-[:LOCATED_IN]-(other_p:Package)
        WHERE NOT (u)-[:ACTION]->(other_p)
        RETURN DISTINCT
            other_p.id AS id,
            COALESCE(other_p.name, other_p.id) AS name,
            COALESCE(other_p.price, 0) AS price,
            COALESCE(other_p.category, 'unknown') AS category,
            city.name AS city,
            city.region AS region
        ORDER BY price ASC
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
        WHERE NOT (:User {id: $user_id})-[:ACTION]->(p)
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
