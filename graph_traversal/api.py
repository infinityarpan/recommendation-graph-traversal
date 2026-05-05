"""FastAPI app factory for the travel recommendation service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import GraphDatabase_Connection
from .routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    GraphDatabase_Connection.initialize()
    try:
        yield
    finally:
        GraphDatabase_Connection.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Travel Recommendation Service",
        version="3.0.0",
        description="Read-only FastAPI service for Neo4j-backed travel recommendations.",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
