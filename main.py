"""ASGI entrypoint for the travel recommendation service."""

from graph_traversal.api import app
from graph_traversal.config import configure_logging


if __name__ == "__main__":
    import uvicorn

    configure_logging()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
