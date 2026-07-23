# Real Estate Recommendation System

AI-powered real estate recommendation system for the Vietnamese market (Ho Chi Minh City). Uses multi-factor scoring, PhoBERT embeddings for semantic search, and Google Gemini for natural language explanations.

## Architecture

| Service | Port | Technology | Purpose |
|---------|------|-----------|---------|
| **Backend** | 8000 | FastAPI + Gunicorn | REST API with property search and AI recommendations |
| **PostgreSQL** | 5432 | pgvector/pgvector:pg16 | Relational data + vector similarity search |
| **Neo4j** | 7474, 7687 | neo4j:5-community | Property similarity graph + knowledge graph |
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
docker compose up -d postgres minio minio-init neo4j

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
