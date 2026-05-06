"""Neo4j graph bootstrap helpers for local and operational seeding."""

import logging

from app.database import get_session

logger = logging.getLogger(__name__)


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
