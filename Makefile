.PHONY: help up down build migrate test lint fmt backend frontend worker shell db-shell

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Docker
up: ## Start all services
	docker compose -f docker/docker-compose.yml --env-file .env.example up -d

down: ## Stop all services
	docker compose -f docker/docker-compose.yml down

build: ## Build all Docker images
	docker compose -f docker/docker-compose.yml --env-file .env.example build

logs: ## Tail logs from all services
	docker compose -f docker/docker-compose.yml logs -f

# Database
migrate: ## Run Alembic migrations
	cd backend && alembic upgrade head

migrate-new: ## Create new migration (usage: make migrate-new MSG="add users table")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	cd backend && alembic downgrade -1

db-shell: ## Open psql shell
	docker compose -f docker/docker-compose.yml exec postgres psql -U listingai -d listingai

# Backend
backend: ## Run backend dev server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
frontend: ## Run frontend dev server
	cd frontend && npm run dev

frontend-install: ## Install frontend dependencies
	cd frontend && npm install

# Worker
worker: ## Run Celery worker
	cd backend && celery -A app.workers.celery_app worker --loglevel=info

beat: ## Run Celery Beat scheduler
	cd backend && celery -A app.workers.celery_app beat --loglevel=info

# Testing
test: ## Run all backend tests
	cd backend && pytest -v

test-cov: ## Run tests with coverage
	cd backend && pytest --cov=app --cov-report=html -v

# Code Quality
lint: ## Run linting
	cd backend && ruff check app/
	cd frontend && npm run lint

fmt: ## Format code
	cd backend && ruff format app/
	cd frontend && npm run format

# Utilities
shell: ## Open backend Python shell
	cd backend && python -c "import asyncio; from app.main import app; print('App loaded')"

redis-cli: ## Open Redis CLI
	docker compose -f docker/docker-compose.yml exec redis redis-cli
