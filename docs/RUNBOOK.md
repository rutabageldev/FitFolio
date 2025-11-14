## Dependencies

### Backend Python Dependencies

The backend uses a three-tier dependency structure:

- **`requirements.txt`**: Core runtime dependencies (production + development)
- **`requirements-dev.txt`**: Development & testing dependencies (includes
  requirements.txt)
- **`requirements-prod.txt`**: Production-specific dependencies (includes
  requirements.txt + gunicorn)

**Docker builds:**

- Dev (`backend/Dockerfile`): Uses `requirements-dev.txt`
- Prod (`backend/Dockerfile.prod`): Uses `requirements-prod.txt`

**Local installation (if not using Docker):**

```bash
# Development
pip install -r backend/requirements-dev.txt

# Production
pip install -r backend/requirements-prod.txt
```

### Frontend Node Dependencies

All frontend dependencies are managed in `frontend/package.json`:

- `dependencies`: Runtime dependencies (React, etc.)
- `devDependencies`: Build tools, linters, formatters

**Install:**

```bash
cd frontend
npm install
```

## Docker Compose Files

- **`compose.dev.yml`**: Development environment (used by default with `make` commands)
- **`compose.prod.yml`**: Production environment (requires building prod images first)

## Production Deploys (Reproducible)

Use immutable image tags to ensure reproducible deployments:

```bash
# Set image coordinates (default owner/repo already in compose)
export GHCR_OWNER=rutabageldev
export GHCR_REPO=fitfolio

# Pin to a specific commit SHA (recommended)
export IMAGE_TAG=sha-$(git rev-parse --short=12 HEAD)

# Deploy
docker compose -f compose.prod.yml pull
docker compose -f compose.prod.yml up -d
```

Rollback by setting `IMAGE_TAG` to a previously known-good SHA and re-running the
pull/up commands.

## Secrets

### Development Preflight

- Verify required dev secrets exist:

```bash
make check-dev-secrets
```

If any are missing, generate them:

```bash
make setup-dev-secrets
```

### Secret Rotation (Production)

1. Create new secrets (keep old ones until services are updated):
   - postgres: `echo "new-password" | docker secret create postgres_password_new -`
   - smtp user: `echo "new-username" | docker secret create smtp_username_new -`
   - smtp pass: `echo "new-password" | docker secret create smtp_password_new -`
2. Update `compose.prod.yml` to point services at the new secret names (or replace the
   existing secrets in place).
3. Deploy:
   `docker compose -f compose.prod.yml pull && docker compose -f compose.prod.yml up -d`
4. Remove old secrets once all services are confirmed healthy.

## Start / Stop

- Start all services (dev): `make up` or `docker compose -f compose.dev.yml up -d`
- Stop all services: `make down`
- See container status: `make ps`
- Tail logs (all): `make logs`
- Tail logs (backend): `make be-logs`
- Tail logs (frontend): `make fe-logs`

## Health Checks

- Backend health: `make health` (or `curl http://localhost:8080/healthz`)
- Frontend dev server: open `http://localhost:5173`

## Dev Email (Mailpit)

- UI: `http://localhost:8025`
- Send test email: `make mail-verify` (uses `/_debug/mail?to=...`)

## Frontend ↔ Backend (dev)

- Vite proxies `/api/*` to backend on `http://localhost:8080`, stripping `/api`.
- Example call from the UI: `fetch('/api/healthz') -> {"status":"ok"}`

## DB Migrations

- Generate migration (autogenerate): `make autogen MSG="description"`

- Apply latest: `make migrate` (or `docker compose exec backend alembic upgrade head`)

- Clean tree check: After applying, run
  `docker compose exec backend alembic revision --autogenerate -m "noop check"` → It
  should produce no operations (delete the noop file if empty).
