.PHONY: help setup up down dev build logs ingest embeddings graph graph-init lint test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## First-time setup: copy .env template
	@cp -n .env.example .env 2>/dev/null || true
	@echo "Created .env from template. Edit it with your values, then run: make up"

up: ## Start all services (postgres, minio, neo4j, backend)
	docker compose up -d

down: ## Stop all services
	docker compose down

dev: ## Run backend locally with hot-reload
	cd backend && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

build: ## Rebuild backend Docker image
	docker compose build backend

logs: ## Tail logs from all services
	docker compose logs -f

ingest: ## Load crawled data into PostgreSQL (INPUT=path/to/file.json)
	python scripts/ingest_data.py --input $(or $(INPUT),crawl_data/data/Final_Data.json)

embeddings: ## Generate PhoBERT embeddings and store in pgvector
	python scripts/generate_embeddings.py

graph-init: ## Initialize Neo4j schema constraints
	docker compose exec -T neo4j cypher-shell -u $$(grep NEO4J_USER .env | cut -d= -f2) -p $$(grep NEO4J_PASSWORD .env | cut -d= -f2) < db/neo4j/init.cypher

graph: ## Populate Neo4j knowledge graph from PostgreSQL data
	python scripts/populate_graph.py --clear

lint: ## Run linters
	cd backend && ruff check src/

test: ## Run tests
	cd backend && pytest tests/ -v

clean: ## Remove containers, volumes, and built images
	docker compose down -v --rmi local
