"""Database operations module for Neo4j"""

import logging
from neo4j import GraphDatabase
from .config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

logger = logging.getLogger(__name__)


class GraphDatabase_Connection:
    """Neo4j database connection handler with lifecycle management"""
    
    _driver = None
    
    @classmethod
    def initialize(cls):
        """Initialize the Neo4j driver with connection pooling"""
        try:
            cls._driver = GraphDatabase.driver(
                NEO4J_URI, 
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
                max_connection_pool_size=50
            )
            # Verify connection
            cls._driver.verify_connectivity()
            logger.info(f"Database connection established to {NEO4J_URI}")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    @classmethod
    def get_driver(cls):
        """Get the Neo4j driver instance"""
        if cls._driver is None:
            cls.initialize()
        return cls._driver
    
    @classmethod
    def close(cls):
        """Close the Neo4j driver connection gracefully"""
        if cls._driver is not None:
            try:
                cls._driver.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
            finally:
                cls._driver = None


def get_session():
    """Get a Neo4j session with default configuration"""
    driver = GraphDatabase_Connection.get_driver()
    return driver.session()
