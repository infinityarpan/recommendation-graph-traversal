# Travel Recommendation Service

Lean FastAPI service for Neo4j-backed travel recommendations. The service is read-only by design: it exposes recommendation and user-stat endpoints while an external clickstream pipeline owns write traffic into Neo4j.

## Project Structure

```text
graph-traversal/
|-- graph_traversal/
|   |-- api.py
|   |-- config.py
|   |-- database.py
|   |-- queries.py
|   |-- routes.py
|   |-- schemas.py
|   `-- services.py
|-- tests/
|-- main.py
|-- requirements.txt
|-- seed_graph.py
`-- README.md
```

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Neo4j access

Create a `.env` file in the repo root:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
LOG_LEVEL=INFO
```

## Run The API

```bash
uvicorn main:app --reload
```

The API is intended for internal use and starts without authentication.

## Seed Local Sample Data

```bash
python seed_graph.py
```

The seed script is manual, repeatable, and non-destructive. It creates:

- Neo4j constraints for stable identifiers
- A compact travel package catalog
- City and destination relationships
- `SIMILAR_TO` package links
- Sample clickstream actions using the standardized model:
  - `viewed`
  - `clicked`
  - `added_to_cart`
  - `booked`
  - `abandoned`

Run the seed against an isolated or local Neo4j instance if you want predictable local test data.

## API Endpoints

- `GET /health`
- `GET /users/{user_id}/recommendations/similar?limit=5`
- `GET /users/{user_id}/recommendations/collaborative?limit=5`
- `GET /users/{user_id}/recommendations/regional?limit=5`
- `GET /users/{user_id}/recommendations/trending?limit=5`
- `GET /users/{user_id}/stats`

## Graph Model

- `(:User)-[:ACTION {type, count, first_action, last_action}]->(:Package)`
- `(:Package)-[:SIMILAR_TO {reason}]->(:Package)`
- `(:Package)-[:LOCATED_IN]->(:City)`

## Development Notes

- The API is read-only in this repo.
- Clickstream ingestion remains available in the query layer for future integration, but no public ingestion route is exposed yet.
- The service uses the synchronous Neo4j driver to keep the codebase small.
