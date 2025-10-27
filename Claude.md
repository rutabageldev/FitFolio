# FitFolio - Project Context for Claude

## Project Overview

**FitFolio** is a personal fitness tracking web application built as a learning platform for modern web development and DevOps best practices. The goal is to allow individuals to define exercise/weightlifting programs, record progress, and perform deeper analysis (trends, correlations, etc.).

**Current Status:** MVP in progress - Magic link authentication is functional, next phase is security hardening and building out the minimal UI.

**Owner:** Personal project for fitness tracking and professional skill development

---

## Architecture

### Tech Stack

**Frontend:**
- React 19.1.0 + Vite 7.0.4
- Modern JavaScript (ES modules)
- ESLint + Prettier for code quality
- TypeScript types (devDependency, not enforced yet)
- Nginx for production serving

**Backend:**
- Python 3.12 + FastAPI 0.116.1
- Uvicorn (dev) / Gunicorn + Uvicorn workers (prod)
- SQLAlchemy 2.0.30 ORM
- Alembic 1.16.4 for migrations
- PostgreSQL 16 database
- Structured logging (structlog) + OpenTelemetry instrumentation

**Authentication:**
- Passwordless: Magic link (email-based) + WebAuthn (passkeys)
- Opaque server-side sessions (SHA-256 hashed tokens)
- HttpOnly, Secure, SameSite=Lax cookies (`ff_sess`)
- 14-day session expiry with rotation infrastructure

**Infrastructure:**
- Containerized: Docker + Docker Compose
- Dev: backend (8080), frontend (5173), postgres (5432), mailpit (8025)
- Prod: backend, frontend, postgres (Traefik + TLS planned in Phase 3)
- Dev Container with Git, Node 20, Docker-outside-of-Docker

**Planned (Not Yet Implemented):**
- Redis for caching and challenge storage
- Vault for runtime secrets injection
- Traefik for reverse proxy + TLS termination
- Full observability stack (OTLP collector, metrics, dashboards)

---

## Project Structure

```
/workspaces/fitfolio/
├── backend/                    # Python/FastAPI backend
│   ├── app/
│   │   ├── api/routes/        # API endpoints (auth, health, dev debug)
│   │   ├── core/              # Business logic (email, security, webauthn)
│   │   ├── db/                # Database (models, session management)
│   │   ├── middleware/        # Request ID tracking
│   │   ├── observability/     # Structlog + OpenTelemetry
│   │   └── main.py            # FastAPI app entry point
│   ├── migrations/            # Alembic migrations
│   ├── requirements*.txt      # Dependencies (core, dev, prod)
│   ├── Dockerfile             # Dev image
│   └── Dockerfile.prod        # Multi-stage prod build
│
├── frontend/                  # React/Vite frontend
│   ├── src/
│   │   ├── App.jsx           # Main component (minimal, needs auth UI)
│   │   └── main.jsx          # Entry point
│   ├── nginx.conf            # Prod nginx config
│   ├── vite.config.js        # Dev server + API proxy to backend
│   ├── package.json
│   ├── Dockerfile            # Dev image
│   └── Dockerfile.prod       # Multi-stage prod build
│
├── .devcontainer/            # Dev container config
├── .github/workflows/ci.yml  # CI pipeline
├── compose.dev.yml           # Dev stack (4 services)
├── compose.prod.yml          # Prod stack (3 services)
├── Makefile                  # Development commands (20+ targets)
├── RUNBOOK.md                # Operational documentation
├── fitfolio_infra_plan.md    # 5-phase roadmap
├── .pre-commit-config.yaml   # Pre-commit hooks
└── .env / env.example        # Environment configuration
```

---

## Development Workflow

### Quick Start

```bash
make up           # Start all services
make logs         # View all logs
make be-logs      # Backend logs only
make fe-logs      # Frontend logs only
make down         # Stop everything
```

### Common Tasks

```bash
# Database
make dbshell      # psql shell
make migrate      # Apply migrations
make autogen MSG="add user table"  # Create migration

# Code Quality
make fmt          # Format code
make lint         # Run pre-commit hooks
make test         # Run pytest (no tests yet)

# Containers
make be           # Shell into backend
make fe           # Shell into frontend
make rebuild      # Rebuild backend image

# Mailpit (dev email)
make mail-ui      # Open Mailpit UI
make mail-verify  # Send test email

# Production
make build-prod   # Build prod images
make up-prod      # Start prod stack
make logs-prod    # View prod logs
```

### Service URLs

- Frontend: http://localhost:5173
- Backend: http://localhost:8080
- Mailpit UI: http://localhost:8025
- API Docs: http://localhost:8080/docs
- Postgres: localhost:5432

---

## Database Schema

**Current Models (4 tables):**

1. **users** - User accounts
   - `id` (UUID PK), `email` (unique, case-insensitive), `is_active`, timestamps, `last_login_at`

2. **sessions** - Opaque server-side sessions
   - `id` (UUID PK), `user_id` (FK), `token_hash` (SHA-256), `created_at`, `expires_at`, `rotated_at`, `revoked_at`, `ip`, `user_agent`
   - Index on `(user_id, expires_at)`

3. **webauthn_credentials** - Passkeys/security keys
   - `id` (UUID PK), `user_id` (FK), `credential_id`, `public_key` (COSE), `sign_count`, `transports`, `nickname`, `backed_up`, `uv_available`, timestamps
   - Unique constraint on `(user_id, nickname)`

4. **login_events** - Audit trail
   - `id` (BigInt PK), `user_id` (FK), `event_type`, `created_at`, `ip`, `user_agent`, `extra` (JSONB)
   - Indexes on `(user_id, created_at)` and `(event_type, created_at)`

---

## API Endpoints

### Health & Debug
- `GET /healthz` - Health check
- `POST /_debug/mail?to=<email>` - Send test email (dev only)

### Magic Link Authentication
- `POST /auth/magic-link/start` - Request magic link (input: `{email}`)
- `POST /auth/magic-link/verify` - Verify token & create session (input: `{token}`)

### WebAuthn (Passkeys)
- `POST /auth/webauthn/register/start` - Begin passkey registration (input: `{email}`)
- `POST /auth/webauthn/register/finish` - Complete registration (input: `{email, credential, challenge}`)
- `POST /auth/webauthn/authenticate/start` - Begin passkey login (input: `{email}`)
- `POST /auth/webauthn/authenticate/finish` - Complete login (input: `{email, credential, challenge}`)

### Session Management
- `GET /auth/me` - Get current user (requires Bearer token or cookie)
- `POST /auth/logout` - Revoke session
- `GET /auth/webauthn/credentials` - List user's passkeys

**Note:** All endpoints return JSON. API is RESTful but OpenAPI docs need enhancement.

---

## Authentication Flow

### Magic Link Flow
1. User submits email → Backend generates secure 32-byte token
2. Token hash (SHA-256) stored in `sessions` table with 15-min TTL
3. Email sent with magic link: `http://localhost:5173/auth/verify?token={token}`
4. User clicks → Frontend calls `/auth/magic-link/verify`
5. Backend validates token hash, creates 14-day session, sets `ff_sess` cookie

### WebAuthn Flow
1. **Registration:** `/register/start` → client creates credential → `/register/finish` → stored in DB
2. **Login:** `/authenticate/start` → client signs challenge → `/authenticate/finish` → session created

### Session Handling
- **Cookie:** `ff_sess` (HttpOnly, SameSite=Lax, Secure in prod, 14-day expiry)
- **Bearer Token:** Alternative for API clients (`Authorization: Bearer <token>`)
- **Token Storage:** Only SHA-256 hash stored in DB (never plaintext)

---

## Code Quality & Security

### Pre-commit Hooks (Auto-run on commit)
- **Ruff** - Python linting + formatting
- **mypy** - Type checking
- **Bandit** - Security static analysis
- **pip-audit** - Dependency vulnerability scanning (pre-push only)
- **detect-secrets** - Secret detection (baseline: `.secrets.baseline`)
- **ESLint + Prettier** - Frontend linting/formatting

**Target:** 95% code coverage (not yet achieved)

### CI/CD (GitHub Actions)
- Pre-commit checks
- Backend tests (pytest - no tests yet)
- Frontend build
- pip-audit
- Migration validation (planned)

**Deployment:** Not automated yet. Plan: Trigger on merge to `main`, move through dev → staging → prod with full observability.

---

## Current Phase: Phase 2 (Auth MVP)

### Completed ✓
- [x] Phase 0: Local dev loop verified
- [x] Phase 1: Database models + Alembic migrations
- [x] Phase 2 (Partial): Magic link + WebAuthn backend endpoints functional
  - [x] Email magic link flow (start/verify)
  - [x] WebAuthn registration/authentication
  - [x] Session management infrastructure
  - [x] `/auth/me` and `/auth/logout` endpoints

### In Progress
- [ ] **Security hardening** (top priority)
  - [ ] Move WebAuthn challenges to server-side storage (Redis or session-based)
  - [ ] Add CSRF protection
  - [ ] Implement rate limiting on auth endpoints
  - [ ] Session rotation activation
  - [ ] Input validation middleware
- [ ] **Frontend auth UI** (minimal MVP)
  - [ ] Magic link request form
  - [ ] Magic link verify page (parse token from URL)
  - [ ] WebAuthn registration flow
  - [ ] WebAuthn login flow
  - [ ] Protected routes with session check
  - [ ] User profile page

### Not Started
- [ ] Phase 3: Traefik + TLS + Docker secrets + Vault
- [ ] Phase 4: Comprehensive testing (pytest, vitest) + CI enhancements
- [ ] Phase 5: Backups, preview environments, full RUNBOOK
- [ ] Feature development: Program creation, workout logging, analytics

---

## Known Security Gaps (CRITICAL)

1. **WebAuthn Challenge Storage** - Challenges currently returned to frontend (can be modified). MUST move to Redis/server-side storage.
2. **No CSRF Protection** - POST endpoints vulnerable to CSRF attacks.
3. **No Rate Limiting** - Auth endpoints can be brute-forced.
4. **CORS Wide Open in Dev** - `allow_methods=["*"]` and `allow_headers=["*"]`.
5. **Magic Link URL Hardcoded** - `http://localhost:5173` in backend code.
6. **No Content-Security-Policy** - Frontend vulnerable to XSS.
7. **Session Rotation Infrastructure Exists But Inactive** - Need to trigger rotation on privilege escalation.

---

## MVP Goal (Phase 2 Complete)

**User Story:** As a user, I can:
1. Sign in via magic link email
2. Register a passkey for future logins
3. Log in with my passkey
4. View my profile
5. Log out

**Next Phase:** Once security is hardened and minimal UI is complete, begin building:
- Program creation (exercise definitions, sets/reps templates)
- Workout logging (record actual sets/reps/weight)
- Progress tracking (history view)

---

## Branching Strategy

- **Main Branch:** Production-ready code. All development happens here until first production release.
- **Post-Prod:** Feature branches for each feature or hotfix, merged to `main` via PR.
- **CI/CD:** Merge to `main` triggers deployment pipeline (not yet built).

---

## Conventions & Best Practices

### Code Style
- **Python:** Ruff formatting (100 char line length), type hints enforced by mypy
- **JavaScript:** ESLint + Prettier, React 19 best practices
- **SQL:** SQLAlchemy ORM with explicit naming conventions (defined in `backend/app/db/base.py`)

### Commit Messages
- Pre-commit hooks run on every commit
- Clear, concise messages describing "why" not "what"
- Use conventional commits format (e.g., `feat:`, `fix:`, `chore:`) when appropriate

### Database Migrations
- Always run `make autogen MSG="description"` to create migrations
- Never edit auto-generated migrations unless necessary
- Test migrations with `alembic upgrade head` and `alembic downgrade -1`

### API Design
- RESTful endpoints
- JSON request/response bodies
- Consistent error responses
- OpenAPI documentation (needs enhancement)
- Validate all inputs with Pydantic

### Secrets Management
- **Dev:** `.env` file (not committed, use `env.example` template)
- **Prod (planned):** Docker secrets + Vault for runtime injection
- **Never commit secrets** - detect-secrets hook prevents this

### Testing (Planned)
- Backend: pytest with async fixtures
- Frontend: Vitest
- E2E: Manual for MVP, automated later
- Coverage target: 95%

---

## Environment Variables

**Key Variables (see `env.example` for full list):**

```bash
# Backend
DATABASE_URL=postgresql+psycopg://fitfolio_user:fitfolio_pass@db:5432/fitfolio
SECRET_KEY=<secure-random-key>
ENVIRONMENT=development  # or production

# Email
SMTP_HOST=mail
SMTP_PORT=1025
SMTP_FROM=noreply@rutabagel.com

# WebAuthn
WEBAUTHN_RP_ID=localhost
WEBAUTHN_RP_NAME=FitFolio
WEBAUTHN_RP_ORIGIN=http://localhost:5173

# CORS
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# OpenTelemetry
OTEL_ENABLED=true
OTEL_OTLP_ENDPOINT=http://localhost:4318
```

---

## Dependencies

### Backend Core (requirements.txt)
- `fastapi==0.116.1` - Web framework
- `uvicorn[standard]==0.29.0` - ASGI server
- `sqlalchemy==2.0.30` - ORM
- `alembic==1.16.4` - Migrations
- `psycopg[binary]>=3.1` - PostgreSQL driver
- `pydantic==2.7.1` - Data validation
- `webauthn>=2.0.0` - WebAuthn/passkey support
- `aiosmtplib>=2.0.1` - Async email
- `structlog>=24.1` - Structured logging
- `opentelemetry-sdk>=1.24` - Observability

### Frontend (package.json)
- `react@^19.1.0` + `react-dom@^19.1.0`
- `vite@^7.0.4` - Build tool
- `eslint@^9.33.0` + `prettier@^3.6.2` - Code quality
- `typescript@^5.9.2` - Type checking (dev only)

---

## Observability

### Logging
- **Format:** Structured JSON logs via structlog
- **Fields:** `timestamp`, `level`, `event`, `request_id`, `logger`, custom context
- **Levels:** DEBUG (dev), INFO (prod)
- **Output:** Console (captured by Docker logs)

### Tracing
- **OpenTelemetry** instrumentation for FastAPI, Psycopg, Requests
- **OTLP Endpoint:** Configured but collector not deployed
- **Request ID:** Middleware adds `X-Request-ID` header for correlation

### Metrics (Planned)
- Prometheus metrics export
- Grafana dashboards
- Health check monitoring

---

## Production Deployment (Planned - Phase 3+)

**Target Domain:** `rutabagel.com`
- Frontend: `/` (served by nginx)
- Backend: `/api` (proxied by Traefik with prefix stripping)
- TLS: Let's Encrypt via Traefik certresolver
- Secrets: Docker secrets (not `.env` files)

**Not Yet Configured:**
- Traefik setup
- TLS certificates
- Production database (currently dev postgres)
- Redis for caching
- Vault for secrets
- Backup/restore procedures
- Horizontal scaling
- Load balancing

---

## Common Issues & Troubleshooting

### "Database connection refused"
- Run `make up` to ensure all containers are running
- Check `make ps` to verify db container is healthy

### "Mailpit not receiving emails"
- Verify `make mail-logs` shows no errors
- Test with `make mail-verify`
- Check `SMTP_HOST=mail` in `.env`

### "Frontend can't reach backend"
- Backend must be accessible at `http://backend:8000` from within Docker network
- Vite proxy config in `vite.config.js` handles `/api` → backend routing

### "Pre-commit hooks failing"
- Run `pre-commit install` to set up hooks
- Run `pre-commit run --all-files` to check all files
- Use `make lint` as shortcut

### "Migrations out of sync"
- Run `make migrate` to apply latest migrations
- Check `alembic current` to see current revision
- Create new migration with `make autogen MSG="description"`

---

## Helpful Context

### Design Decisions

1. **Passwordless-only:** No password support. Magic link + WebAuthn provides better security and UX.
2. **Opaque sessions:** Token hashing prevents token leakage even if DB is compromised.
3. **WebAuthn from day one:** Passkeys are the future; building it in from the start.
4. **Single host routing:** `/api` prefix avoids CORS complexity in production.
5. **Structured logging:** JSON logs enable easy parsing and search in centralized logging.
6. **Alembic auto-generation:** Migrations generated from SQLAlchemy models reduce errors.

### Performance Considerations (Future)
- Redis for session storage (faster than PostgreSQL)
- Database connection pooling (already configured via SQLAlchemy)
- CDN for static assets
- Nginx caching
- WebP image format for photos
- Lazy loading for large workout history

### Accessibility (Future)
- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support
- High contrast mode

---

## Questions to Ask Me

If you need clarification on any of the following, please ask:

1. **Specific business logic** - How should programs/workouts be structured?
2. **UI/UX preferences** - Design system, component library, styling approach?
3. **Priority of features** - Which features are most important for MVP?
4. **Deployment timeline** - When do I want to go to production?
5. **Third-party services** - Any preference for observability tools, error tracking, etc.?
6. **Mobile support** - PWA? Native app? Responsive web only?

---

## Additional Resources

- [RUNBOOK.md](./RUNBOOK.md) - Operational procedures
- [fitfolio_infra_plan.md](./fitfolio_infra_plan.md) - 5-phase implementation roadmap
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [WebAuthn Guide](https://webauthn.guide/)
- [Alembic Docs](https://alembic.sqlalchemy.org/)
- [Vite Docs](https://vite.dev/)

---

**Last Updated:** 2025-10-27 (Auto-generated by Claude based on codebase exploration)
