# Real Estate Recommendation System

Hybrid real-estate search for the Vietnamese market. Uses validated structured
filters, PostgreSQL full-text search, multilingual-E5 embeddings in pgvector,
evidence-based reranking and deterministic explanations.

## Hybrid search V1

The serving path now uses PostgreSQL and pgvector only; Neo4j is not required for
search. Vietnamese natural-language queries are parsed into validated hard filters,
amenity-distance constraints and semantic preferences. Hard constraints are applied
in parameterized SQL before full-text/vector retrieval and deterministic reranking.

```text
POST /v1/search/parse
POST /v1/search
POST /v1/search/similar/{listing_id}
```

Prepare a fresh local database (run from the repository root):

```bash
docker compose up -d --build backend

# Imports Final_Data.csv, graph-ready amenity distances and builds search_text.
docker compose exec backend \
  python scripts/build_search_index.py --skip-embeddings

# Downloads multilingual-e5-large once and resumes missing pgvector embeddings.
docker compose exec -e SEARCH_ALLOW_MODEL_DOWNLOAD=true backend \
  python scripts/build_search_index.py --skip-catalog-import \
  --skip-graph-metadata --batch-size 32
```

Semantic retrieval is enabled only when every active listing has an embedding. Until
then `/v1/search` remains available in structured + PostgreSQL full-text mode and
reports embedding coverage when `debug=true`.

## Architecture

| Service | Port | Technology | Purpose |
|---------|------|-----------|---------|
| **Backend** | 8000 | FastAPI + Gunicorn | REST API with property search and AI recommendations |
| **PostgreSQL** | 5432 | pgvector/pgvector:pg16 | Relational data + vector similarity search |
| **Neo4j (optional)** | 7474, 7687 | neo4j:5-community | Offline graph inspection only; not used by search serving |
| **MinIO** | 9000, 9001 | minio/minio | S3-compatible object storage for property images |

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (only for local backend development)
- A Google Gemini API key (for AI search features)

### Option 1: Docker Compose (all services)

```bash
cp .env.example .env
# Edit .env — set your passwords and GEMINI_API_KEYS

docker compose up -d
docker compose ps        # all services should be running
```

### Option 2: Docker infra + local backend

Run databases in Docker, backend locally with hot-reload.

```bash
cp .env.example .env
# Edit .env — change:
#   HOST_DB=localhost
#   MINIO_END_POINT=localhost:9000
#   NEO4J_URI=bolt://localhost:7687

# Start infra only
docker compose up -d postgres minio minio-init

# Optional graph inspection tools only
docker compose --profile graph-tools up -d neo4j

# Run backend locally
cd backend
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Service URLs

| URL | Service |
|-----|---------|
| http://localhost:8000 | Backend API (Swagger docs at `/`) |
| http://localhost:7474 | Neo4j Browser |
| http://localhost:9001 | MinIO Console |

## Project Structure

```
CS2307/
├── backend/               FastAPI application
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py
│       ├── api/v1/        REST endpoints
│       ├── services/      Database, inference, LLM, MinIO, recommendation
│       ├── settings/      Config, events, middleware
│       └── utils/
├── frontend/              Next.js application
├── crawl_data/            Data scraping scripts
├── docker-compose.yml     All services
├── .env.example           Environment template
└── .gitignore
```

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `GEMINI_API_KEYS` | Google Gemini API key(s), comma-separated |
| `HOST_DB` | `postgres` (Docker) or `localhost` (local dev) |
| `MINIO_END_POINT` | `minio:9000` (Docker) or `localhost:9000` (local dev) |
| `NEO4J_AUTH` | Format: `neo4j/<password>` |

See `.env.example` for the full list.
