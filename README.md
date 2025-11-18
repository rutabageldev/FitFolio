# FitFolio

**Modern fitness tracking application with passwordless authentication and comprehensive security.**

[![CI - Quality Gate](https://github.com/rutabageldev/fitfolio/actions/workflows/ci-quality-gate.yml/badge.svg?branch=main)](https://github.com/rutabageldev/fitfolio/actions/workflows/ci-quality-gate.yml) [![Coverage](https://img.shields.io/badge/coverage-97.9%25-brightgreen)]() [![Python](https://img.shields.io/badge/python-3.12-blue)]()

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Dev Container support (VS Code or Cursor recommended)

### First-Time Dev Container Setup

1. **Open the project** in VS Code or Cursor
2. **Reopen in Container** when prompted (or use Command Palette: "Dev Containers: Reopen in Container")
3. **One-time**: Accept the prompt to install the Claude Code extension (if using Claude)
4. **All other tools install automatically**: Python dependencies, Docker CLI, Node.js, Claude CLI, Git configuration, SSH setup, and pre-commit hooks

After the initial setup, all subsequent container rebuilds will preserve your Claude conversation history and settings.

### Run Locally

```bash
# Open in dev container (VS Code/Cursor) - RECOMMENDED
# Or manually:
docker compose -f compose.dev.yml up

# Frontend: http://localhost:5173
# Backend API: http://localhost:8080
# API Docs: http://localhost:8080/docs
# Mailpit: http://localhost:8025
```

### Run Tests

```bash
make test
# Or: cd backend && pytest
```

### Test Database (Postgres)

For representative testing (INET/JSONB/TZ), prefer Postgres for tests. Create a dedicated test DB once per environment, then point tests at it:

```bash
# 1) Create the test database (idempotent)
bash scripts/setup_test_db.sh

# 2) Run tests against Postgres
export TEST_DATABASE_URL=postgresql+psycopg://fitfolio_user:supersecret@db:5432/fitfolio_test
cd backend && pytest -q -ra
```

Notes:

- Tests isolate state using a per-session schema; the database persists between runs for speed.
- If running outside devcontainer/compose, set PGHOST/PGPORT/PGUSER/PGPASSWORD before running the setup script.

---

## Features

### Authentication & Security ✅

- **Passwordless Authentication**
  - Magic link via email (primary)
  - WebAuthn/Passkeys (biometric, security keys)
- **Enterprise-Grade Security**
  - CSRF protection (double-submit cookie)
  - Rate limiting (per-IP, per-endpoint)
  - Account lockout (5 failed attempts = 15 min)
  - Email verification (required before login)
  - Session rotation (7-day automatic + event-based)
- **Session Management**
  - View active sessions across devices
  - Revoke individual or all sessions
  - Automatic cleanup of expired data
- **Audit Logging**
  - Complete auth event trail
  - Admin query endpoints with filtering

### Core Fitness Features 🔮

_Coming after Phase 3 deployment:_

- Workout program management
- Exercise logging with metrics
- Progress analytics and insights
- Integration with sleep/nutrition data

---

## Technology

- Backend: Python (FastAPI), SQLAlchemy, PostgreSQL, Redis, Alembic
- Frontend: React, Vite, TypeScript
- Infrastructure: Docker/Compose, Traefik, Nginx, Gunicorn/Uvicorn
- Quality & Observability: pytest, pre-commit (ruff/mypy/bandit), structlog, OpenTelemetry

---

## Project Status & Planning

For the latest status and plans, see:

- Roadmap: `docs/ROADMAP.md`
- Changelog: `docs/CHANGELOG.md`

---

## Documentation

| Document                                                        | Purpose                                   |
| --------------------------------------------------------------- | ----------------------------------------- |
| [ROADMAP.md](docs/ROADMAP.md)                                   | Outstanding work and next steps           |
| [CHANGELOG.md](docs/CHANGELOG.md)                               | Historical record of completed work       |
| [RUNBOOK.md](docs/RUNBOOK.md)                                   | Operational procedures and commands       |
| [DOCKER_SECRETS.md](docs/development/DOCKER_SECRETS.md)         | Secrets in development and production     |
| [STAGING.md](docs/deployment/STAGING.md)                        | Staging domain, secrets, deploy/promotion |
| [backend/CSRF_INTEGRATION.md](docs/backend/CSRF_INTEGRATION.md) | CSRF implementation details               |
| [Design System](docs/design/README.md)                          | Brand, foundations, components, patterns  |

---

## Architecture Highlights

### Authentication Flow

1. **Magic Link (Primary)**

   - User enters email → receives magic link
   - Link valid for 15 minutes, single-use
   - Email verification required before first login
   - Creates server-side session on success

2. **WebAuthn/Passkeys (Optional)**
   - Prompted after first magic link login
   - Biometric or security key authentication
   - Faster subsequent logins
   - Challenge stored in Redis (30-60s TTL)

### Security Model

- Opaque sessions, token hashing, secure cookies, session rotation
- Rate limiting, CSRF protection
- See `docs/backend/` and ADRs (`docs/adr/`) for details

---

## API

- OpenAPI docs (local): `http://localhost:8080/docs`
- Base path: `/api/v1/`

---

## Development

### Project Structure

```
fitfolio/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/v1/   # Versioned API routes
│   │   ├── core/     # Business logic
│   │   ├── db/       # Database models & connection
│   │   └── middleware/ # CSRF, rate limiting, etc.
│   ├── migrations/   # Alembic database migrations
│   └── tests/        # See test catalog in docs/
│
├── frontend/         # React frontend
│   ├── src/
│   └── vite.config.js
│
├── docs/             # Documentation
├── .devcontainer/    # Dev container config
└── compose.*.yml     # Docker Compose configs
```

### Common Tasks

```bash
# Development
make up          # Start dev environment
make down        # Stop dev environment
make logs        # View logs
make test        # Run tests
make shell       # Backend shell

# Database
make migrate     # Run migrations
make autogen     # Generate new migration

# Code Quality
make lint        # Run linters
make format      # Format code
pre-commit run --all-files  # Run all checks
```

---

## Testing

- Start at: `docs/testing/README.md`
- Catalog reports: `docs/testing/catalog/backend/report.json`
- Coverage badge above is auto-updated by CI

---

## Security

- Audits: bandit (static analysis), pip-audit (dependency vulnerabilities)
- Reporting: please report privately (full process to be published post-public launch)

---

## License

_License TBD_

---

## Contributing

_Contributing guidelines TBD_

---

## Acknowledgments

Built with:

- Modern Python async patterns
- FastAPI best practices
- Industry-standard security controls
- Test-driven development
- Comprehensive pre-commit quality gates

**Development Approach:**

- Security-first mindset
- 100% test coverage for security-critical code
- Continuous quality enforcement
- Industry best practices

---

Deployment and operations: see `docs/RUNBOOK.md` and `docs/deployment/STAGING.md`.
