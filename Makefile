.PHONY: help up down ps be-health rebuild be-logs fe-logs logs be fe dbshell migrate autogen fmt lint test mail-logs mail-verify mail-ui open-mailpit open-frontend build-prod up-prod down-prod logs-prod

help:        ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*##/: /'

up:          ## Start the whole stack (backend, db, frontend)
	docker compose up -d --build

down:        ## Stop and remove containers
	docker compose down

ps:
	docker compose ps

be-health: # Backend Health Check
	\tcurl -sS http://localhost:8080/healthz

rebuild:     ## Rebuild backend image then start
	docker compose build backend
	docker compose up -d

be-logs:        ## Follow backend logs
	docker compose logs -f --tail=200 backend

fe-logs:
	docker compose logs -f frontend

logs:
	docker compose logs -f

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
	pre-commit run --all-files || true

test:        ## Run backend tests
	docker compose exec backend bash -lc "pytest -q"

mail-logs:
	docker compose logs -f mail

mail-ui:
	( xdg-open http://localhost:8025 || open http://localhost:8025 || powershell.exe start http://localhost:8025 ) >/dev/null 2>&1 || true

mail-verify:
	curl -sS -X POST "http://localhost:8080/_debug/mail?to=you@rutabagel.com"

open-mailpit:
	@echo "Mailpit UI -> http://localhost:8025"

open-frontend:
	@echo "Frontend -> http://localhost:5173"

build-prod:
	docker build -f backend/Dockerfile.prod -t fitfolio-backend:prod .
	docker build -f frontend/Dockerfile.prod -t fitfolio-frontend:prod .

up-prod: build-prod
	docker compose -f compose.prod.yml up -d

down-prod:
	docker compose -f compose.prod.yml down -v

logs-prod:
	docker compose -f compose.prod.yml logs -f --tail=200
