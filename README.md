# FitFolio

**Modern fitness tracking application with passwordless authentication and comprehensive security.**

[![Tests](https://img.shields.io/badge/tests-93%20passing-success)]() [![Security](https://img.shields.io/badge/security-A+-success)]() [![Python](https://img.shields.io/badge/python-3.12-blue)]() [![FastAPI](https://img.shields.io/badge/FastAPI-0.120-009688)]() [![React](https://img.shields.io/badge/React-19-61dafb)]()

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

*Coming after Phase 3 deployment:*
- Workout program management
- Exercise logging with metrics
- Progress analytics and insights
- Integration with sleep/nutrition data

---

## Technology Stack

### Backend
- **Python 3.12** - Modern async Python
- **FastAPI 0.120** - High-performance async web framework
- **SQLAlchemy 2.0** - Async ORM with type hints
- **PostgreSQL 16** - Primary database
- **Redis 7** - Caching, sessions, rate limiting
- **Alembic** - Database migrations

### Frontend
- **React 19** - Latest React with modern features
- **Vite 7** - Fast build tool and dev server
- **TypeScript** - Type-safe frontend code

### Infrastructure
- **Docker + Compose** - Containerized development and deployment
- **Nginx** - Production frontend serving
- **Gunicorn + Uvicorn** - Production WSGI/ASGI server
- **Traefik** *(coming in Phase 3)* - Reverse proxy with automatic TLS

### Quality & Observability
- **pytest** - 93 tests with 100% pass rate
- **Pre-commit hooks** - Automated quality gates (ruff, mypy, bandit)
- **structlog** - Structured JSON logging
- **OpenTelemetry** - Distributed tracing

---

## Project Status

**Current Phase:** Phase 2B Complete ✅
**Next Phase:** Phase 3 - Production Deployment

### Completed ✅
- ✅ Phase 0: Local development environment
- ✅ Phase 1: Database schema & migrations
- ✅ Phase 2A: Core security (CSRF, rate limiting, session rotation)
- ✅ Phase 2B: Security hardening (lockout, email verification, audit logging)
- ✅ API versioning (directory-based `/api/v1/`)
- ✅ 93 comprehensive tests

### Up Next 🔄
- [ ] Phase 3: Production deployment (Traefik, TLS, Docker Secrets)
- [ ] Phase 4: CI/CD pipeline (GitHub Actions)
- [ ] Phase 5: Observability & operations (backups, monitoring)

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed planning.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [ROADMAP.md](docs/ROADMAP.md) | Outstanding work and next steps |
| [CHANGELOG.md](docs/CHANGELOG.md) | Historical record of completed work |
| [RUNBOOK.md](docs/RUNBOOK.md) | Operational procedures and commands |
| [backend/CSRF_INTEGRATION.md](docs/backend/CSRF_INTEGRATION.md) | CSRF implementation details |

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

- **Opaque Sessions**: Server-side only, no JWT exposure
- **Token Hashing**: SHA-256 for all stored tokens
- **Cookie Security**: HttpOnly, Secure, SameSite=Lax
- **Session Rotation**: Automatic after 7 days or privilege changes
- **Rate Limiting**: Token bucket algorithm, per-IP tracking
- **CSRF Protection**: Double-submit cookie pattern

### Database Schema

5 core tables:
- `users` - User accounts with email verification
- `sessions` - Server-side session storage with rotation
- `magic_link_tokens` - Single-use email tokens (login + verification)
- `webauthn_credentials` - Passkey public keys
- `login_events` - Comprehensive audit log

---

## API Endpoints

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/magic-link/start` | Request magic link via email |
| POST | `/magic-link/verify` | Verify magic link token |
| POST | `/webauthn/register/start` | Start passkey registration |
| POST | `/webauthn/register/finish` | Complete passkey registration |
| POST | `/webauthn/authenticate/start` | Start passkey authentication |
| POST | `/webauthn/authenticate/finish` | Complete passkey authentication |
| GET | `/webauthn/credentials` | List user's passkeys |
| POST | `/logout` | End current session |
| GET | `/me` | Get current user info |

### Email Verification (`/api/v1/auth/email`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/verify` | Verify email with token |
| POST | `/resend-verification` | Resend verification email |

### Session Management (`/api/v1/auth/sessions`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | List active sessions |
| DELETE | `/{id}` | Revoke specific session |
| POST | `/revoke-all-others` | Revoke all other sessions |

### Admin (`/api/v1/admin`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/audit/events` | Query audit logs (filtered) |
| GET | `/audit/event-types` | List available event types |

**Full API Documentation:** http://localhost:8080/docs (when running locally)

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
│   └── tests/        # 93 comprehensive tests
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

### Test Coverage

**93 tests across 8 test suites:**
- `test_security.py` (14) - Token generation, hashing, validation
- `test_csrf.py` (14) - CSRF protection middleware
- `test_session_rotation.py` (16) - Session rotation logic
- `test_rate_limiting.py` (9) - Rate limiting per endpoint
- `test_account_lockout.py` (7) - Failed login tracking
- `test_email_verification.py` (11) - Email verification flow
- `test_audit_logging.py` (11) - Audit event logging
- `test_session_management.py` (11) - Session management & cleanup

**100% pass rate** | **1.83s runtime** | **Pre-commit integrated**

---

## Security

### Threat Model

**Protected Against:**
- ✅ Brute force attacks (rate limiting + account lockout)
- ✅ CSRF attacks (double-submit cookie pattern)
- ✅ Session hijacking (rotation + secure cookies)
- ✅ Token replay (single-use tokens, Redis TTL)
- ✅ Email enumeration (consistent timing, error messages)
- ✅ Unverified accounts (email verification required)

### Security Audits

- **bandit** - Static security analysis (pre-commit)
- **pip-audit** - Dependency vulnerability scanning (pre-commit)
- Manual code review for auth-critical paths

### Reporting Security Issues

Please report security vulnerabilities privately (details TBD after public deployment).

---

## License

*License TBD*

---

## Contributing

*Contributing guidelines TBD*

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

**Current Status:** Phase 2B Complete - Production-Ready Security Infrastructure
**Next Milestone:** Deploy to production (Phase 3)

For questions or support, see [docs/RUNBOOK.md](docs/RUNBOOK.md).
