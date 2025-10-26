.PHONY: help up down ps be-health rebuild be-logs fe-logs logs be fe dbshell migrate autogen fmt lint test mail-logs mail-verify mail-ui open-mailpit open-frontend build-prod up-prod down-prod logs-prod

help:        ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*##/: /'

up:          ## Start the whole stack (backend, db, frontend)
	docker compose -f compose.dev.yml up -d --build

down:        ## Stop and remove containers
	docker compose -f compose.dev.yml down

ps:
	docker compose -f compose.dev.yml ps

be-health: # Backend Health Check
	\tcurl -sS http://localhost:8080/healthz

rebuild:     ## Rebuild backend image then start
	docker compose -f compose.dev.yml build backend
	docker compose -f compose.dev.yml up -d

be-logs:        ## Follow backend logs
	docker compose -f compose.dev.yml logs -f --tail=200 backend

fe-logs:
	docker compose -f compose.dev.yml logs -f frontend

logs:
	docker compose -f compose.dev.yml logs -f

be:          ## Shell into backend container
	docker compose -f compose.dev.yml exec backend bash

fe:          ## Shell into frontend container
	docker compose -f compose.dev.yml exec frontend sh

dbshell:     ## psql into the DB (uses env from the container)
	docker compose -f compose.dev.yml exec db psql -U fitfolio_user -d fitfolio

migrate:     ## Apply latest Alembic migrations
	alembic -c backend/alembic.ini upgrade head

autogen:     ## Create a new Alembic migration from models
	@if [ -z "$(MSG)" ]; then echo 'Set MSG="your message"'; exit 1; fi
	alembic -c backend/alembic.ini revision --autogenerate -m "$(MSG)"

fmt:         ## Format Python (ruff/black if you add them)
	docker compose -f compose.dev.yml exec backend bash -lc "ruff format || true; black . || true"

lint:        ## Lint (pre-commit if you use it)
	pre-commit run --all-files || true

test:        ## Run backend tests
	docker compose -f compose.dev.yml exec backend bash -lc "pytest -q"

mail-logs:
	docker compose -f compose.dev.yml logs -f mail

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
