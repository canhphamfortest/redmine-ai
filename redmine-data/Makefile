.PHONY: help build up down logs clean seed test

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

build: ## Build all Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d
	@echo "Services starting..."
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@echo ""
	@echo "✅ Services are running!"
	@echo "📊 Streamlit UI: http://localhost:8501"
	@echo "🔌 FastAPI Docs: http://localhost:8000/docs"
	@echo "🏥 API Health: http://localhost:8000/health"

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## Show logs from all services
	docker-compose logs -f

logs-backend: ## Show backend logs
	docker-compose logs -f backend

logs-streamlit: ## Show streamlit logs
	docker-compose logs -f streamlit

logs-scheduler: ## Show scheduler logs
	docker-compose logs -f scheduler

ps: ## Show running containers
	docker-compose ps

clean: ## Stop and remove all containers, volumes
	docker-compose down -v
	docker system prune -f

db-shell: ## Access PostgreSQL shell
	docker exec -it rag-postgres psql -U postgres -d rag_db

redis-cli: ## Access Redis CLI
	docker exec -it rag-redis redis-cli

backend-shell: ## Access backend container shell
	docker exec -it rag-backend bash

sync-openai-config: ## Sync OpenAI default pricing to database
	@echo "Syncing OpenAI default pricing..."
	@curl -s -X POST http://localhost:8000/api/openai-config/sync-defaults || \
		(echo "⚠️  Backend may not be running. Start services with: make up" && exit 1)
	@echo "✅ OpenAI config synced!"

seed: ## Seed database with sample data
	docker exec rag-backend python scripts/seed_data.py

fix-embeddings: ## Fix embedding dimension mismatch (check only)
	docker exec rag-backend python scripts/fix_embedding_dimensions.py --check-only

fix-embeddings-dry: ## Fix embedding dimension mismatch (dry run)
	docker exec rag-backend python scripts/fix_embedding_dimensions.py --dry-run

fix-embeddings-run: ## Fix embedding dimension mismatch (actually fix)
	docker exec rag-backend python scripts/fix_embedding_dimensions.py

fix-embeddings-regen: ## Fix and regenerate embeddings
	docker exec rag-backend python scripts/fix_embedding_dimensions.py --regenerate

test: ## Run tests
	docker exec rag-backend pytest tests/ -v

db-migrate: ## Run database migrations
	docker exec rag-backend alembic upgrade head

db-reset: ## Reset database (WARNING: deletes all data)
	docker exec rag-postgres psql -U postgres -d rag_db -f /docker-entrypoint-initdb.d/init_db.sql

backup-db: ## Backup database
	docker exec rag-postgres pg_dump -U postgres rag_db > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db: ## Restore database from backup (usage: make restore-db FILE=backup.sql)
	docker exec -i rag-postgres psql -U postgres rag_db < $(FILE)

stats: ## Show system stats
	@echo "=== Docker Stats ==="
	docker stats --no-stream
	@echo ""
	@echo "=== Database Stats ==="
	docker exec rag-postgres psql -U postgres -d rag_db -c "\
		SELECT 'Sources' as table, COUNT(*) FROM source \
		UNION ALL SELECT 'Chunks', COUNT(*) FROM chunk \
		UNION ALL SELECT 'Embeddings', COUNT(*) FROM embedding;"

dev: ## Start in development mode with hot reload
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

prod: ## Start in production mode
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d