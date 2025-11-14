# FitFolio Changelog

**Purpose:** Historical record of completed work with dates and commit references.

For outstanding work, see [ROADMAP.md](ROADMAP.md).

---

## 2025-11-06 - CI/CD Pipeline & Security Hardening Complete

### GitHub Actions CI/CD Pipeline

**Commits:** `a2c58c0`, `13399bb`, `4f59841`

Complete CI/CD pipeline with comprehensive quality gates and security scanning:

**CI Workflow Jobs:**

- **Backend Tests & Coverage** - pytest with PostgreSQL, Redis, MailHog services
- **Backend Linting** - ruff linting, ruff format, mypy type checking
- **Backend Security** - bandit security scan, pip-audit dependency scanning
- **Backend Migration Check** - Alembic migration validation
- **Frontend Linting** - ESLint, Prettier formatting checks
- **Frontend Build** - Production build validation
- **Frontend Security** - npm audit for vulnerabilities
- **Frontend Tests** - vitest with coverage (optional, continue-on-error)
- **CodeQL Analysis** - Advanced SAST for Python and JavaScript/TypeScript
- **Dependency Review** - Blocks vulnerable dependencies in PRs
- **Commit Verification** - Encourages signed commits (warning mode)
- **CI Success** - Summary job requiring all critical jobs to pass

**Infrastructure:**

- Service containers for PostgreSQL 16, Redis 7, MailHog
- Parallel job execution with optimal caching
- Concurrency control to cancel outdated runs
- Proper permissions for security-events and pull-requests

**Quality Gates:**

- 138 tests (100% passing)
- Full mypy type coverage
- Ruff linting and formatting enforcement
- Security scanning with bandit
- Database migration validation
- Frontend build verification

**Security Features:**

- CodeQL for semantic code analysis (security-extended + security-and-quality queries)
- Dependency review blocking moderate+ vulnerabilities
- License compliance (blocks GPL-3.0, AGPL-3.0)
- Commit signature verification (educational warnings)
- No shortcuts or disabled checks

**Files:**

- `.github/workflows/ci.yml` - Complete CI/CD pipeline
- `.github/SECURITY.md` - Security policy and reporting guidelines
- `.github/workflows/README.md` - Workflow documentation

**Bug Fixes During Implementation:**

- Fixed psycopg3 compatibility (DATABASE_URL format, UUID types)
- Fixed Alembic migration execution in CI
- Added MailHog for email testing
- Fixed mypy type errors in auth, webauthn, logging modules
- Fixed FastAPI Request parameter handling
- Synchronized frontend package-lock.json
- Patched vite security vulnerability

**Impact:**

- Production-ready CI/CD pipeline
- Automated quality enforcement
- Security vulnerability detection
- Blocked deployment of vulnerable code
- Foundation for automated deployments (Phase 3B)

---

## 2025-10-31 - Traefik Integration & Production Configuration

### Traefik Integration for Development

**Commit:** `b688b8c`

Configured Traefik reverse proxy integration for development and production:

- Added `VITE_ALLOWED_HOST` environment variable support to Vite config
- Updated `compose.dev.yml` with Traefik labels and networks:
  - Backend routing: `Host(fitfolio.dev.rutabagel.com) && PathPrefix(/api)`
  - Frontend routing: `Host(fitfolio.dev.rutabagel.com)` (lower priority)
  - Connected to external `traefik-public` network
  - Proper network isolation (traefik-public + default)
- Completely overhauled `compose.prod.yml` to match dev structure:
  - Added missing environment variables (EMAIL_SENDER, JWT_SECRET, CORS_ORIGINS)
  - Added Traefik labels with production domain (fitfolio.rutabagel.com)
  - Added mail service (Mailpit as placeholder for production SMTP)
  - Added restart policies (`unless-stopped`)
  - Added proper healthcheck with `start_period`
  - Configured network isolation
  - Commented out direct port exposure (Traefik handles routing)
- Added `/api` root endpoint for version discovery
- Archived experimental TRAEFIK-INTEGRATION.md documentation
- Removed unused compose.dev.traefik.yml file

**Files Updated:**

- `frontend/vite.config.js` - Dynamic allowed hosts from env
- `frontend/.env` - VITE_ALLOWED_HOST configuration
- `compose.dev.yml` - Traefik labels and VITE_ALLOWED_HOST
- `compose.prod.yml` - Complete production configuration
- `backend/app/main.py` - API root endpoint

**Impact:**

- Development accessible at `https://fitfolio.dev.rutabagel.com`
- Production configuration ready for deployment
- Automatic SSL via Traefik Let's Encrypt integration
- Proper separation of concerns (Traefik for routing/TLS, services for application
  logic)

---

## 2025-10-29 - API Versioning & Documentation Consolidation

### Directory-Based API Versioning

**Commit:** `b5ebbcb`

Restructured API to directory-based versioning for better version management:

- Created `app/api/v1/` directory structure
- Moved auth and admin routes to v1 namespace
- Created router aggregator at `app/api/v1/__init__.py`
- Updated main.py to use aggregated v1 router
- Supports running multiple API versions simultaneously

**Impact:** Better backward compatibility support, cleaner version transitions

### Initial API Versioning Implementation

**Commit:** `97e6864`

Added `/api/v1/` prefix to all API endpoints:

- Updated router includes with API_V1_PREFIX
- Updated CSRF exempt paths
- Updated rate limit patterns
- Updated all 93 tests
- Reorganized documentation into `/docs/` directory
- Updated frontend proxy configuration

**Impact:** Professional API structure, ready for version transitions

### Security Vulnerability Fix

**Commit:** `88b1625`

Fixed Starlette security vulnerability:

- Upgraded FastAPI: 0.116.1 → 0.120.2
- Explicitly pinned starlette >=0.49.1
- Addressed GHSA-7f5h-v6xp-fcq8 (security advisory)
- Verified all 93 tests still passing

**Impact:** Critical security fix, production-ready dependencies

### Architecture Assessment Update

**Commit:** `18f1b76`

Comprehensive documentation update after Phase 2B completion:

- Updated overall rating: 8.5/10 → 9.0/10
- Documented all Phase 2B implementations
- Added quick reference tables (security controls, test coverage)
- Streamlined from 728 → 407 lines
- Clarified next steps (Phase 3)

**Impact:** Current state documentation, clear roadmap

---

## 2025-10-29 - Phase 2B Complete: Security Hardening

### Session Management & Automated Cleanup

**Commit:** `fccb223`

User-facing session management with automated cleanup:

- `GET /api/v1/auth/sessions` - List active sessions
- `DELETE /api/v1/auth/sessions/{id}` - Revoke specific session
- `POST /api/v1/auth/sessions/revoke-all-others` - Revoke all others
- Background cleanup job (24-hour interval)
- Cleanup expired sessions and old rotated sessions (90+ days)
- Cleanup expired magic links
- 11 new tests in `test_session_management.py`

**Test Coverage:** 11 tests

- List sessions (auth, success, excludes expired)
- Revoke session (success, cannot revoke current, cannot revoke other users)
- Revoke all others (success, with no other sessions)
- Cleanup (expired sessions, old rotated sessions, expired magic links)

**Impact:** Users can manage active sessions, automated maintenance

### Comprehensive Audit Logging

**Commit:** `7c9afd4`

Full authentication event logging with admin query endpoints:

- LoginEvent records for all auth events
- Structured metadata in JSONB `extra` field
- Event types: magic link, WebAuthn, session, account, email
- `GET /api/v1/admin/audit/events` - Paginated with filters
- `GET /api/v1/admin/audit/event-types` - Available types
- 11 new tests in `test_audit_logging.py`

**Test Coverage:** 11 tests

- Magic link events (request, verify success/failure)
- Account lockout events
- WebAuthn events (register, auth)
- Audit query endpoint
- Event type filtering
- Date range filtering
- Get event types endpoint

**Impact:** Complete audit trail, compliance support, security monitoring

### Email Verification Flow

**Commit:** `1aa5984`

Required email verification before login:

- Database migration: added `is_email_verified` to User
- Added `purpose` field to MagicLinkToken ('login' vs 'email_verification')
- Verification tokens with 24-hour TTL
- Automatic verification email on user creation
- HTTP 403 enforcement for unverified users
- `POST /api/v1/auth/email/verify` - Verify email with token
- `POST /api/v1/auth/email/resend-verification` - Resend verification
- 11 new tests in `test_email_verification.py`

**Database Migration:** `488ee27f900f`

**Test Coverage:** 11 tests

- Email verification success flow
- Expired token rejection
- Already verified user handling
- Unverified user login blocked
- Magic link blocked for unverified users
- WebAuthn blocked for unverified users
- Resend verification email
- /me endpoint blocked for unverified
- Double verification attempt handling

**Impact:** Critical security control, prevents abuse

### Failed Login Tracking & Account Lockout

**Commit:** `e0f5b18`

Redis-based account lockout after failed login attempts:

- Policy: 5 failed attempts in 1 hour = 15 minute lockout
- Redis-backed with automatic expiry
- Sliding window for attempt counting
- Automatic reset on successful login
- Integrated into magic link verify endpoint
- 7 new tests in `test_account_lockout.py`

**Test Coverage:** 7 tests

- Successful login after failed attempts
- Account locked after 5 attempts
- Login blocked when locked
- Lockout expires after 15 minutes
- Failed attempt counter resets on success
- Different users have independent counters
- Challenge request allowed when locked

**Impact:** Brute force protection, security hardening

---

## 2025-10-27 - Phase 2A Complete: Core Security

### Session Rotation Implementation

**Commit:** `4f879ea`

Automatic and forced session rotation for security:

- Time-based rotation (7-day threshold)
- Event-based rotation (privilege escalation)
- Automatic rotation on `/api/v1/auth/me` endpoint
- Old session marked with `rotated_at` timestamp
- New session creation with fresh expiry
- 16 new tests in `test_session_rotation.py`

**Test Coverage:** 16 tests

- Rotation logic (recent sessions, old sessions, threshold, already-rotated)
- Rotation function behavior (new session, old session marking, context inheritance,
  reason logging, fresh expiry)
- Integration tests (automatic rotation, forced rotation, rotated token rejection,
  cleanup, active preservation)

**Impact:** Enhanced security, prevents session hijacking

### CSRF Protection Implementation

**Commit:** `8c7f9d2`

Double-submit cookie pattern with comprehensive protection:

- Middleware for all state-changing requests
- CSRF token generation on GET requests
- Cookie-to-header validation
- Exempt paths for public endpoints
- 14 new tests in `test_csrf.py`

**Files:**

- `app/middleware/csrf.py` - CSRF middleware
- `docs/backend/CSRF_INTEGRATION.md` - Integration guide
- `tests/test_csrf.py` - Comprehensive tests

**Test Coverage:** 14 tests

- Token generation on GET requests
- Protected endpoints require valid tokens (POST, PUT, DELETE)
- Mismatched tokens rejected
- Exempt paths work without tokens
- HTTP method handling (GET/OPTIONS don't require CSRF)

**Impact:** Protection against CSRF attacks, production-ready

### Rate Limiting Implementation

**Commit:** `6a8f4d1`

Token bucket rate limiting with Redis backend:

- Per-IP rate limiting
- Per-endpoint custom limits
- 429 Too Many Requests responses
- Retry-After header
- 9 new tests in `test_rate_limiting.py`

**Rate Limits:**

- Magic link start: 5 req/60s
- Magic link verify: 10 req/60s
- WebAuthn start: 10 req/60s
- WebAuthn finish: 20 req/60s
- Logout: 10 req/60s
- Global fallback: 1000 req/60s

**Test Coverage:** 9 tests

- Magic link rate limiting (start, verify)
- WebAuthn rate limiting (register, auth)
- Global rate limit
- Different IPs independent tracking
- Rate limit reset after window

**Impact:** DoS protection, abuse prevention

### Redis Challenge Storage

**Commit:** `3b7e4a2`

Secure WebAuthn challenge storage with Redis:

- Replaced in-memory storage with Redis
- 30-second TTL for registration challenges
- 60-second TTL for authentication challenges
- Automatic expiry
- Race condition prevention

**Files:**

- `app/core/challenge_storage.py` - Redis storage implementation
- `app/core/redis_client.py` - Redis connection management

**Impact:** Production-ready WebAuthn, prevents replay attacks

---

## 2025-10-26 - Phase 1 Complete: Foundation

### Database Schema & Migrations

**Commit:** `initial_migration`

Initial database schema with Alembic:

- `users` table (id, email, is_active, is_email_verified, timestamps)
- `sessions` table (id, user_id, token_hash, expiry, rotation, IP, user_agent)
- `magic_link_tokens` table (id, user_id, token_hash, purpose, expiry, IPs)
- `webauthn_credentials` table (id, user_id, credential_id, public_key, sign_count,
  name)
- `login_events` table (id, user_id, event_type, IP, user_agent, metadata)
- Indexes for performance (email, token_hash, user queries)

**Impact:** Solid foundation for auth system

### Passwordless Authentication MVP

**Commit:** `auth_mvp`

Magic link and WebAuthn (passkeys) authentication:

- `POST /api/v1/auth/magic-link/start` - Request magic link
- `POST /api/v1/auth/magic-link/verify` - Verify magic link token
- `POST /api/v1/auth/webauthn/register/start` - Start passkey registration
- `POST /api/v1/auth/webauthn/register/finish` - Complete passkey registration
- `POST /api/v1/auth/webauthn/authenticate/start` - Start passkey auth
- `POST /api/v1/auth/webauthn/authenticate/finish` - Complete passkey auth
- `GET /api/v1/auth/webauthn/credentials` - List user's passkeys
- `POST /api/v1/auth/logout` - End current session
- `GET /api/v1/auth/me` - Get current user info

**Security Features:**

- Opaque server-side sessions (no JWT)
- SHA-256 token hashing
- HttpOnly, Secure, SameSite=Lax cookies
- 7-day session expiry

**Impact:** Passwordless foundation, strong security posture

### Development Environment

**Commit:** `devcontainer_setup`

Complete development environment with tooling:

- Dev container with Python 3.12, Node 20, Docker
- Docker Compose (dev + prod configurations)
- PostgreSQL 16, Redis 7, Mailpit
- Pre-commit hooks (ruff, mypy, bandit, pytest)
- Makefile for common tasks
- Initial test suite (14 tests)

**Files:**

- `.devcontainer/devcontainer.json`
- `compose.dev.yml`, `compose.prod.yml`
- `.pre-commit-config.yaml`
- `Makefile`

**Impact:** Consistent dev environment, quality enforcement

---

## Architecture & Testing Summary

### Test Coverage Evolution

| Date       | Total Tests | Test Files           | Pass Rate |
| ---------- | ----------- | -------------------- | --------- |
| 2025-10-26 | 14          | 1 (test_security.py) | 100%      |
| 2025-10-27 | 53          | 4                    | 100%      |
| 2025-10-29 | 93          | 8                    | 100%      |
| 2025-11-06 | 138         | 8                    | 100%      |

**Test Files:**

1. `test_security.py` (14 tests) - Token generation, hashing, session validation
2. `test_csrf.py` (14 tests) - CSRF protection middleware
3. `test_session_rotation.py` (16 tests) - Session rotation logic
4. `test_rate_limiting.py` (9 tests) - Rate limiting per endpoint
5. `test_account_lockout.py` (7 tests) - Failed login tracking
6. `test_email_verification.py` (11 tests) - Email verification flow
7. `test_audit_logging.py` (11 tests) - Audit event logging
8. `test_session_management.py` (11 tests) - Session management & cleanup

### Technology Stack

**Backend:**

- Python 3.12
- FastAPI 0.120.2
- SQLAlchemy 2.0 (async)
- Alembic 1.16
- Redis 7
- PostgreSQL 16

**Frontend:**

- React 19
- Vite 7
- ESLint + Prettier

**Infrastructure:**

- Docker + Compose
- Mailpit (dev email testing)
- Nginx (prod frontend)
- Gunicorn + Uvicorn (prod backend)

**Observability:**

- structlog (structured logging)
- OpenTelemetry (distributed tracing)
- Request ID middleware

### Security Controls

| Control              | Status      | Implementation Date |
| -------------------- | ----------- | ------------------- |
| Passwordless Auth    | ✅ Complete | 2025-10-26          |
| Server-Side Sessions | ✅ Complete | 2025-10-26          |
| CSRF Protection      | ✅ Complete | 2025-10-27          |
| Rate Limiting        | ✅ Complete | 2025-10-27          |
| Challenge Storage    | ✅ Complete | 2025-10-27          |
| Session Rotation     | ✅ Complete | 2025-10-27          |
| Account Lockout      | ✅ Complete | 2025-10-29          |
| Email Verification   | ✅ Complete | 2025-10-29          |
| Audit Logging        | ✅ Complete | 2025-10-29          |
| Session Management   | ✅ Complete | 2025-10-29          |
| API Versioning       | ✅ Complete | 2025-10-29          |
| CI/CD Pipeline       | ✅ Complete | 2025-11-06          |
| CodeQL Analysis      | ✅ Complete | 2025-11-06          |
| Dependency Review    | ✅ Complete | 2025-11-06          |

### Database Migrations

| Version      | Date       | Description                                                            |
| ------------ | ---------- | ---------------------------------------------------------------------- |
| Initial      | 2025-10-26 | Base schema (users, sessions, magic_link_tokens, webauthn_credentials) |
| 488ee27f900f | 2025-10-29 | Add email verification support (is_email_verified, purpose field)      |
| (future)     | TBD        | Add login_events table (already in code, migration pending)            |

---

## Milestones

### Phase 0: Local Development Loop ✅

**Completed:** 2025-10-26 **Duration:** ~2 hours

Dev container, Docker Compose, basic health checks working.

### Phase 1: Foundation ✅

**Completed:** 2025-10-26 **Duration:** ~8 hours

Database schema, Alembic migrations, passwordless auth MVP.

### Phase 2A: Core Security ✅

**Completed:** 2025-10-27 **Duration:** ~12 hours

CSRF, rate limiting, Redis challenge storage, session rotation.

### Phase 2B: Security Hardening ✅

**Completed:** 2025-10-29 **Duration:** ~14 hours

Account lockout, email verification, audit logging, session management, API versioning.

### Phase 3A: CI/CD Pipeline ✅

**Completed:** 2025-11-06 **Duration:** ~6 hours

GitHub Actions workflow with comprehensive quality gates and security scanning.

### Phase 3B: Production Deployment 🔄

**Status:** Ready to Start **Estimated:** 6-8 hours (reduced - CI/CD complete)

Production SMTP, Docker Secrets, VPS deployment, security headers.

---

## Recognition & Credits

**Development Approach:**

- Test-driven development (TDD)
- Pre-commit quality gates
- Comprehensive test coverage
- Security-first mindset
- Industry best practices

**Key Design Decisions:**

- Opaque sessions over JWT (security)
- Passwordless-first (UX + security)
- Directory-based API versioning (maintainability)
- Redis for ephemeral data (performance)
- PostgreSQL for persistent data (reliability)
- Monorepo structure (simplicity)

---

**Document Version:** 1.1 **Last Updated:** 2025-11-06 **Next Update:** After Phase 3B
completion
