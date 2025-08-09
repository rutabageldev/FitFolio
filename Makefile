# Makefile (repo root)
.PHONY: help up down rebuild logs be fe dbshell migrate autogen fmt lint test

help:        ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*##/: /'

up:          ## Start the whole stack (backend, db, frontend)
	docker compose up -d

down:        ## Stop and remove containers
	docker compose down

rebuild:     ## Rebuild backend image then start
	docker compose build backend
	docker compose up -d

logs:        ## Follow backend logs
	docker compose logs -f --tail=200 backend

be:          ## Shell into backend container
	docker compose exec backend bash

fe:          ## Shell into frontend container
	docker compose exec frontend sh

dbshell:     ## psql into the DB (uses env from the container)
	docker compose exec db psql -U fitfolio_user -d fitfolio

migrate:     ## Apply latest Alembic migrations
	docker compose exec backend bash -lc "cd backend && alembic upgrade head"

autogen:     ## Create a new Alembic migration from models
	docker compose exec backend bash -lc "cd backend && alembic revision --autogenerate -m \"auto\""

fmt:         ## Format Python (ruff/black if you add them)
	docker compose exec backend bash -lc "ruff format || true; black . || true"

lint:        ## Lint (pre-commit if you use it)
	docker compose exec backend bash -lc "pre-commit run --all-files || true"

test:        ## Run backend tests
	docker compose exec backend bash -lc "pytest -q"
