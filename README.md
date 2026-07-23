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
- Python 3.9+ (only needed for Option 2 and data scripts)
- A Google Gemini API key (for AI search features)

### Option 1: Docker Compose (recommended)

Everything runs in containers. No local Python needed.

```bash
# 1. Clone
git clone <repo-url> && cd CS2307

# 2. Setup environment
cp .env.example .env
# Edit .env — set your GEMINI_API_KEYS and passwords

# 3. Start all services
docker compose up -d

# 4. Verify
docker compose ps                          # all services should be "healthy"
curl http://localhost:8000/health           # {"status": "ok"}
```

### Option 2: Local backend + Docker services

Run PostgreSQL/MinIO/Neo4j in Docker, but the backend locally with hot-reload (useful for development).

```bash
# 1. Clone and setup
git clone <repo-url> && cd CS2307
cp .env.example .env

# 2. Edit .env — change HOST_DB to localhost (instead of "postgres")
#    HOST_DB=localhost
#    MINIO_END_POINT=localhost:9000
#    NEO4J_URI=bolt://localhost:7687

# 3. Start only infrastructure services
docker compose up -d postgres minio minio-init neo4j

# 4. Install Python dependencies and run backend
cd backend
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Make shortcuts

If you have `make` installed:

```bash
cp .env.example .env          # edit with your values
make up                       # start all services (docker compose up -d)
make logs                     # tail logs
make down                     # stop all services

# Or for local dev:
make dev                      # runs uvicorn with hot-reload
```

## Loading Data

The database starts empty. To populate it:

```bash
# 1. Crawl data (if you don't have JSON files yet)
cd crawl_data
pip install -r requirements.txt
python crawl_full_details.py         # outputs to crawl_data/data/

# 2. Ingest into PostgreSQL
#    (set HOST_DB=localhost if running script outside Docker)
HOST_DB=localhost python scripts/ingest_data.py --input crawl_data/data/Final_Data.json

# 3. Generate embeddings
HOST_DB=localhost python scripts/generate_embeddings.py

# 4. Populate Neo4j graph
HOST_DB=localhost NEO4J_URI=bolt://localhost:7687 python scripts/populate_graph.py --clear
```

## Services URLs

| URL | Service |
|-----|---------|
| http://localhost:8000 | Backend API (Swagger docs at `/`) |
| http://localhost:7474 | Neo4j Browser |
| http://localhost:9001 | MinIO Console |

## Project Structure

```
CS2307/
├── backend/                    FastAPI application
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   └── src/
│       ├── main.py             App entry point (/health endpoint)
│       ├── api/v1/endpoints/   REST endpoints (properties, ai-search)
│       ├── services/
│       │   ├── database/       PostgreSQL connector
│       │   ├── inference/      Scoring, normalization, knowledge base
│       │   ├── llm/            Gemini LLM integration
│       │   ├── minio/          Object storage client
│       │   └── recommendation/ AI recommendation pipeline (PhoBERT)
│       ├── settings/           Config, events, middleware
│       └── utils/
├── crawl_data/                 Data scraping scripts (batdongsan.com.vn)
├── db/
│   ├── postgres/               SQL schema (auto-runs on first docker start)
│   └── neo4j/                  Cypher constraints and indexes
├── scripts/
│   ├── ingest_data.py          Load JSON → PostgreSQL
│   ├── generate_embeddings.py  PhoBERT embeddings → pgvector
│   └── populate_graph.py       PostgreSQL → Neo4j graph
├── deploy/
│   ├── setup-vm.sh             GCE VM provisioning
│   ├── setup-gke.sh            GKE cluster + Artifact Registry
│   ├── install.sh              VM bootstrap script
│   └── README.md               Deployment guide (VM + GKE)
├── k8s/                        Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml          Postgres init SQL
│   ├── secrets.yaml.example    Secrets template
│   ├── postgres.yaml           StatefulSet + PVC
│   ├── minio.yaml              StatefulSet + PVC + init Job
│   ├── neo4j.yaml              StatefulSet + PVC
│   ├── backend.yaml            Deployment (2 replicas)
│   └── ingress.yaml            LoadBalancer service
├── .github/workflows/
│   └── deploy.yml              CI/CD: build → Artifact Registry → GKE
├── docker-compose.yml
├── .env.example
└── Makefile
```

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `GEMINI_API_KEYS` | Yes | Google Gemini API key(s), comma-separated |
| `HOST_DB` | Yes | `postgres` (Docker) or `localhost` (local dev) |
| `MINIO_END_POINT` | Yes | `minio:9000` (Docker) or `localhost:9000` (local dev) |
| `NEO4J_AUTH` | Yes | Format: `neo4j/<password>` |

See `.env.example` for the full list with defaults.


## Cloud Deployment

Two options — see [`deploy/README.md`](deploy/README.md) for full guide.

**Option 1: Single VM** — quick setup, ~$110/month
```
bash deploy/setup-vm.sh → gcloud ssh → install.sh → docker compose up
```

**Option 2: GKE + CI/CD** — auto-scaling, automated deploys, ~$200-300/month
```
bash deploy/setup-gke.sh → setup GitHub secrets → git push → auto-deploy
```
