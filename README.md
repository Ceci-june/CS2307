# Real Estate Recommendation System

Hybrid real-estate search for the Vietnamese market. Uses validated structured
filters, PostgreSQL full-text search, multilingual-E5 embeddings in pgvector,
Neo4j relationship retrieval, evidence-based reranking and deterministic explanations.

## Hybrid search V1

PostgreSQL remains the source of truth while Neo4j is an optional online candidate
and evidence source. Vietnamese natural-language queries are parsed into validated
hard filters, amenity-distance constraints and semantic preferences. PostgreSQL
FTS/pgvector candidates and Neo4j traversal candidates are merged before deterministic
reranking. Search falls back to PostgreSQL when Neo4j is unavailable.

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

### GPU embedding

`SEARCH_EMBEDDING_DEVICE=auto` automatically selects CUDA, then Apple MPS, then CPU.
You can explicitly select `cpu`, `cuda`, `cuda:0`, or `mps`. If the requested GPU is
unavailable or model transfer fails, embedding safely falls back to CPU.

For an NVIDIA GPU exposed to Docker, apply the GPU override:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml \
  --profile graph-search up -d --build backend
```

Apple MPS works when the backend/index script runs directly on macOS; Docker Desktop's
Linux VM does not expose MPS. Search debug output includes `embedding_device` and
`embedding_gpu`. Adjust `--batch-size` when building the index to fit GPU memory.

### Enable Neo4j graph search

Set `SEARCH_USE_NEO4J=true` in `.env`, then start and import the graph:

```bash
docker compose --profile graph-search up -d neo4j
docker compose exec neo4j sh -lc \
  '/var/lib/neo4j/bin/cypher-shell -u "$GRAPH_USER" -p "$GRAPH_PASSWORD" \
  -f /opt/search-graph/import_search_graph.cypher'

docker compose --profile graph-search up -d --build backend
```

Use `debug=true` on `/v1/search` to inspect graph availability, candidate count and
latency. `/v1/search/similar/{listing_id}` also combines vector similarity with shared
ward, street, geo-cluster and amenity relationships.

## Database migrations

PostgreSQL schema changes are versioned with Alembic. The backend Docker container
automatically applies pending migrations before starting Gunicorn. For local
development, migrate before starting the API:

```bash
cd backend
alembic upgrade head
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Useful commands:

```bash
alembic current
alembic history --verbose
alembic revision -m "describe schema change"
alembic downgrade -1
```

The same operations are available through `make db-upgrade`, `make db-current`,
`make db-history`, `make db-downgrade`, and
`make db-revision m="describe schema change"`. Review a downgrade and back up the
database before running it; downgrading the initial revision removes its tables.

Revisions are written explicitly because the project currently uses SQL queries
without declarative ORM models. See `backend/migrations/README.md` for details.

## Architecture

| Service | Port | Technology | Purpose |
|---------|------|-----------|---------|
| **Backend** | 8000 | FastAPI + Gunicorn | REST API with property search and AI recommendations |
| **PostgreSQL** | 5432 | pgvector/pgvector:pg16 | Relational data + vector similarity search |
| **Neo4j (optional)** | 7474, 7687 | neo4j:5-community | Online graph candidates, relationship evidence and similar-listing traversal |
| **MinIO** | 9000, 9001 | minio/minio | S3-compatible object storage for property images |

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (only for local backend development)
- A Gemini key or an OpenAI-compatible endpoint (for AI search features)

### Option 1: Docker Compose (all services)

```bash
cp .env.example .env
# Edit .env — set your passwords and LLM provider credentials

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
│   ├── Makefile           Short database migration commands
│   ├── alembic.ini
│   ├── migrations/        Versioned PostgreSQL schema changes
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
| `BACKEND_LLM_PROVIDER` | `gemini`, `openai`, `openai-compatible`, `groq`, or `grok` |
| `BACKEND_LLM_MODEL` | Model name sent to the selected provider |
| `BACKEND_LLM_BASE_URL` | Base URL for a custom OpenAI-compatible endpoint |
| `BACKEND_LLM_API_KEY` | API key for an OpenAI-compatible endpoint |
| `GEMINI_API_KEYS` | Gemini API key(s), comma-separated (Gemini only) |
| `HOST_DB` | `postgres` (Docker) or `localhost` (local dev) |
| `MINIO_END_POINT` | `minio:9000` (Docker) or `localhost:9000` (local dev) |
| `NEO4J_AUTH` | Format: `neo4j/<password>` |

To switch the backend to an OpenAI-compatible server, only the provider settings
need to change; application code and API routes stay the same:

```dotenv
BACKEND_LLM_PROVIDER=openai-compatible
BACKEND_LLM_MODEL=qwen2.5:14b
BACKEND_LLM_BASE_URL=http://host.docker.internal:11434/v1
BACKEND_LLM_API_KEY=
```

For OpenAI, Groq, and Grok, `BACKEND_LLM_BASE_URL` is optional because the
backend includes their standard API URLs. Set the matching model and key, for
example `BACKEND_LLM_PROVIDER=openai`, `BACKEND_LLM_MODEL=gpt-4o-mini`, and
`BACKEND_LLM_API_KEY=...`.

See `.env.example` for the full list.
