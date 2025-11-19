# FitFolio Changelog

All notable completed work is documented here. For outstanding work, see
[ROADMAP.md](ROADMAP.md).

---

## 2025-11-17 - Staging Continuous Deployment & Promotion Gate

### Deployment Automation

**Staging CD (GitHub Actions)**

- Added automated deploys to staging after CI/build success
- Workflow: `cd-staging-promote.yml`
  - Gates on successful runs of:
    - `CI - Quality Gate` (tests, lint, security, build)
    - `CD - Build and Push Images` (publishes `backend` and `frontend` images)
  - Idempotent: skips if a successful promotion for the same SHA already ran
  - Computes immutable `IMAGE_TAG` as `sha-<12char>`
  - Verifies GHCR images exist for both services
  - SSH deploy to staging with stack sync and environment-scoped secrets
  - Runs DB migrations via a one-off service before app traffic
  - Waits for backend health and Traefik TLS issuance
  - Executes smoke tests against `https://fitfolio-staging.rutabagel.com`

**Coverage Badge Automation**

- Workflow: `ci-update-coverage-badge.yml`
  - Updates README coverage badge on `main` after successful CI
  - Pulls badge artifact from `CI - Quality Gate`

**CI Quality Gate Enhancements**

- Workflow: `ci-quality-gate.yml`
  - Parallelized jobs for backend tests/coverage, linting, security (bandit, pip-audit),
    CodeQL, DB migrations check, frontend lint/build/audit
  - Coverage badge artifact generation and PR comment with % coverage

**Benefits:**

- Reproducible, gated staging releases tied to commit SHAs
- Safer migrations via dedicated one-off service
- Immediate validation via smoke tests and TLS checks
- Automatic coverage signal in README and PRs

**Environment:**

- Staging domain: `fitfolio-staging.rutabagel.com`
- Immutable images in GHCR: `ghcr.io/rutabageldev/fitfolio/{backend,frontend}:sha-<12>`

---

## 2025-11-14 - Docker Secrets & Dev/Prod Parity

### Security Infrastructure

**Docker Secrets Migration**

- Implemented Docker Swarm secrets for production deployment
- Created `app/core/secrets.py` module for secure secret reading
- Updated `compose.prod.yml` to use external Docker secrets
- Added comprehensive production secrets documentation
- Secrets: `postgres_password`, `smtp_username`, `smtp_password`

**Development Environment Parity**

- Added file-based Docker secrets to development environment
- Created `scripts/setup-dev-secrets.sh` for automated secret generation
- Updated `compose.dev.yml` to mount secrets from `.secrets/` directory
- Added `make setup-dev-secrets` command for easy developer onboarding
- Created development secrets documentation

**Benefits:**

- Same code paths for secret reading in dev and production
- Secret injection mechanism tested before production deployment
- Enhanced security practices throughout development lifecycle
- Easier debugging of secret-related issues in development

**Pull Request:** #5 (In Progress)

---

## 2025-11-13 - Code Quality & Static Analysis

### CodeQL Warnings Resolution

**Production Code Fixes**

- Fixed unused global variable warnings in `app/core/redis_client.py`
- Added `_redis_url_cache` to global declarations
- Ensured proper cleanup in `close_redis()` function

**Test Code Improvements**

- Added explanatory comments to empty except blocks
- Removed unnecessary lambda wrappers in `test_cleanup.py`
- Replaced ellipsis stubs with `pass` statements (7 instances)
- Fixed import inconsistencies (`from app.db import database`)
- Added explicit returns after `pytest.fail()` calls

**Results:**

- Resolved 20+ CodeQL static analysis warnings
- All 397 tests passing
- Coverage maintained at 94.37%
- Pre-commit hooks passing

**Pull Request:** #4

---

## 2025-11-06 - Test Coverage Improvement

### Phase 3A.5: Test Coverage (41% → 97.81%)

**Critical Achievement:** Improved test coverage from 41% to 97.81% - exceeding 85%
target

**Handler-Level Test Coverage**

- Magic link authentication (start, verify, error paths)
- Email verification workflows
- WebAuthn registration and authentication
- Session management and rotation
- Account lockout mechanisms
- CSRF protection
- Rate limiting

**Coverage by Module:**

- `app/api/deps.py`: 34% → 100%
- `app/api/v1/admin.py`: 38% → 86.49%
- `app/api/v1/auth.py`: 99.78%
- `app/core/*`: 91-100% across all modules
- `app/middleware/*`: 97-100%
- `app/main.py`: 100%

**Test Statistics:**

- Total tests: 138 → 397 tests
- Pass rate: 100%
- Coverage: 41.29% → 97.81%
- All critical modules above 85%

**Infrastructure:**

- Added coverage enforcement to CI (85% minimum)
- Created test catalog system for tracking coverage
- Handler-level vs integration test distinction
- Comprehensive error path testing

**Pull Request:** #3

---

## 2025-11-06 - CI/CD Pipeline & Security Hardening

### Phase 3A: CI/CD Pipeline Complete

**GitHub Actions Workflow**

- Comprehensive CI pipeline for pull requests
- Parallel job execution with optimal caching
- Service containers (PostgreSQL, Redis, MailHog)
- Concurrency control (cancel outdated runs)

**Quality Gates**

- ✅ Backend tests (138 → 397 tests, 100% passing)
- ✅ Backend linting (ruff, mypy)
- ✅ Backend security (bandit, pip-audit)
- ✅ Backend migration validation (alembic check)
- ✅ Frontend linting (ESLint, Prettier)
- ✅ Frontend build validation
- ✅ Frontend security audit (npm audit)

**Security Scanning**

- ✅ CodeQL analysis (Python + JavaScript/TypeScript)
- ✅ Dependency review (blocks vulnerable dependencies)
- ✅ Commit verification (warning mode)
- ✅ No security shortcuts or bypasses

**Results:**

- All quality gates passing
- Zero security vulnerabilities
- 97.81% test coverage
- Production-ready CI/CD infrastructure

---

## 2025-10-31 - Traefik Integration

### Phase 2B: Reverse Proxy Setup

**Development Environment**

- Configured Traefik labels in `compose.dev.yml`
- Set up routing for `fitfolio.dev.rutabagel.com`
- Backend routing: `Host() && PathPrefix(/api)` (priority 10)
- Frontend routing: `Host()` (priority 1)
- TLS configuration with automatic certificates

**Production Configuration**

- Updated `compose.prod.yml` with Traefik labels
- Configured for `fitfolio.rutabagel.com`
- Network isolation (traefik-public + default networks)
- Service healthchecks and restart policies

**Architecture Decision**

- ADR-0002: Use existing Traefik instance
- Traefik handles reverse proxy + TLS
- Nginx remains in frontend for static file serving

**Results:**

- Development domain working with HTTPS
- Automatic TLS certificate issuance
- Proper routing between frontend and backend
- Production configuration ready

---

## 2025-10-29 - API Versioning

### Phase 2A: API Organization

**Directory-Based Versioning**

- Implemented `/api/v1/` prefix for all endpoints
- Created `app/api/v1/auth.py` route module
- Added API root endpoint (`/api`) for version discovery
- Updated all frontend API calls

**Architecture Decision**

- ADR-0001: Directory-based API versioning
- Chosen over header or query parameter versioning
- Aligns with FastAPI best practices
- Clear URL structure for clients

**Results:**

- Clean API versioning strategy
- All endpoints under `/api/v1/`
- Easy to add v2 in future
- Documented in ADR

---

## 2025-10-26 - Authentication Foundation

### Phase 1 & 2: Passwordless Authentication

**Magic Link Authentication**

- Email-based passwordless authentication
- Secure token generation and validation
- Rate limiting and account lockout
- Email verification workflow

**WebAuthn Support**

- Passkey registration and authentication
- Challenge-response protocol
- Credential management
- Multi-device support

**Session Management**

- Opaque server-side sessions (PostgreSQL)
- Session rotation on sensitive operations
- Concurrent session tracking
- Device fingerprinting

**Security Features**

- CSRF protection middleware
- Rate limiting middleware
- Request ID tracking
- Account lockout (5 failures, 15-minute lockout)
- Secure cookie configuration (HttpOnly, Secure, SameSite)

**Architecture Decisions**

- ADR-0003: Passwordless authentication strategy
- ADR-0004: Opaque server-side sessions
- Focus on security and user experience

**Results:**

- Production-ready authentication system
- Multiple authentication methods
- Comprehensive security controls
- 138 passing tests

---

## Project Foundation

### Initial Setup

**Backend Stack**

- FastAPI framework
- PostgreSQL database
- Redis for sessions and caching
- Alembic for migrations
- SQLAlchemy ORM

**Frontend Stack**

- React with TypeScript
- Vite build tool
- React Router
- Axios for API calls

**Development Tools**

- Pre-commit hooks (ruff, mypy, prettier, eslint)
- Docker Compose for local development
- MailHog for email testing
- Comprehensive linting and formatting

**Security Baseline**

- Bandit security scanning
- pip-audit for dependency vulnerabilities
- npm audit for frontend security
- Secret scanning (detect-secrets)

---

## Future Work

See [ROADMAP.md](ROADMAP.md) for planned features and improvements.

**Next Major Milestones:**

1. Production deployment (Phase 3B)
2. Production monitoring and operations (Phase 4)
3. Feature development (Phase 5)
   - Program management
   - Workout logging
   - Analytics and insights
   - External integrations
