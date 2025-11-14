.PHONY: help setup-dev-secrets check-dev-secrets up down ps be-health rebuild be-logs fe-logs logs be fe dbshell migrate autogen fmt lint test test-parity mail-logs mail-verify mail-ui magic-link open-mailpit open-frontend build-prod up-prod down-prod logs-prod

help:        ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*##/: /'

setup-dev-secrets:  ## Setup development Docker secrets
	@bash scripts/setup-dev-secrets.sh

check-dev-secrets:  ## Check if development secrets are configured
	@bash scripts/check-dev-secrets.sh

up: check-dev-secrets  ## Start the whole stack (backend, db, frontend)
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

test-parity: ## Run tests with RL on and isolated Redis DB (db=1). Usage: make test-parity ARGS='path::to::test -k pattern'
	docker compose -f compose.dev.yml exec backend bash -lc "REDIS_URL=redis://redis:6379/1 RATE_LIMIT_ENABLED=true pytest -q -ra $(ARGS)"

mail-logs:
	docker compose -f compose.dev.yml logs -f mail

mail-ui:
	( xdg-open http://localhost:8025 || open http://localhost:8025 || powershell.exe start http://localhost:8025 ) >/dev/null 2>&1 || true

mail-verify:
	curl -sS -X POST "http://localhost:8080/_debug/mail?to=you@rutabagel.com"

magic-link:  ## Request magic link and open Mailpit UI
	@echo "Requesting magic link for test@example.com..."
	@docker exec fitfolio-backend curl -sS -X POST http://localhost:8000/api/v1/auth/magic-link/start \
		-H "Content-Type: application/json" \
		-d '{"email": "test@example.com"}' | python3 -m json.tool
	@echo ""
	@echo "✓ Magic link sent! Check Mailpit UI at http://localhost:8025"
	@( xdg-open http://localhost:8025 || open http://localhost:8025 || powershell.exe start http://localhost:8025 ) >/dev/null 2>&1 || true

open-mailpit:
	@echo "Mailpit UI -> http://localhost:8025"

open-frontend:
	@echo "Frontend -> http://localhost:5173"

up-staging: ## Start staging stack
	docker compose -f compose.staging.yml up -d

down-staging: ## Stop staging stack
	docker compose -f compose.staging.yml down -v

logs-staging: ## Tail staging logs
	docker compose -f compose.staging.yml logs -f --tail=200

migrate-staging: ## Apply DB migrations in staging
	docker compose -f compose.staging.yml exec backend bash -lc "alembic -c /app/alembic.ini upgrade head"

smoke-staging: ## Quick staging smoke tests
	@echo "Health check -> https://staging.fitfolio.rutabagel.com/healthz"
	@curl -fsS -I https://staging.fitfolio.rutabagel.com/healthz | head -n 1
	@echo "API root -> https://staging.fitfolio.rutabagel.com/api"
	@curl -fsS https://staging.fitfolio.rutabagel.com/api | python3 -m json.tool || true

build-prod:
	docker build -f backend/Dockerfile.prod -t fitfolio-backend:prod .
	docker build -f frontend/Dockerfile.prod -t fitfolio-frontend:prod .

up-prod: build-prod
	docker compose -f compose.prod.yml up -d

down-prod:
	docker compose -f compose.prod.yml down -v

logs-prod:
	docker compose -f compose.prod.yml logs -f --tail=200
