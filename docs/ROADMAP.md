# FitFolio Roadmap

**Last Updated:** 2025-10-29
**Current Phase:** Phase 3 - Production Deployment

This document tracks **outstanding work only**. For completed work history, see [CHANGELOG.md](CHANGELOG.md).

---

## Phase 3: Production Deployment

**Status:** 🔄 Ready to Start
**Estimated Effort:** 10-12 hours (reduced from 12-16 by leveraging existing Traefik)
**Target:** Deploy production-ready system to utility node (existing VPS)

### Prerequisites

- ✅ All Phase 2B security work complete
- ✅ 93 tests passing
- ✅ API versioning implemented
- ✅ Pre-commit hooks enforcing quality

### Tasks

#### 1. Traefik Integration (2-3 hours)

**Decision:** Use existing Traefik instance (already running UniFi + Vaultwarden)

Add FitFolio to existing Traefik setup via Docker labels:

- [ ] Update `compose.prod.yml` with Traefik labels:
  - Backend routing: `Host(rutabagel.com) && PathPrefix(/api)`
  - Frontend routing: `Host(rutabagel.com)` (lower priority)
  - TLS cert resolver: `letsencrypt` (existing)
  - HTTP → HTTPS redirect
- [ ] Connect FitFolio services to `traefik-net` network (existing)
- [ ] Configure security headers middleware:
  - HSTS (Strict-Transport-Security)
  - CSP (Content-Security-Policy)
  - X-Frame-Options, X-Content-Type-Options
- [ ] Test deployment on utility node
- [ ] Verify automatic TLS certificate issuance
- [ ] Verify routing (frontend, backend, health checks)

**Architecture:** Traefik handles reverse proxy + TLS, Nginx stays in frontend container for static file serving

**Reference:** See [docs/REVERSE_PROXY_ANALYSIS.md](REVERSE_PROXY_ANALYSIS.md) for detailed comparison

**Acceptance Criteria:**
- HTTPS works on `rutabagel.com`
- TLS certificate auto-issued via Let's Encrypt
- Backend accessible at `/api/v1/*`
- Frontend serves at `/` (all other routes)
- Security headers present in responses
- HTTP redirects to HTTPS
- No CORS errors in production

#### 2. Docker Secrets (2-3 hours)

Replace `.env` file with Docker secrets for production:

- [ ] Create secret files for sensitive values:
  - `db_password`
  - `redis_password`
  - `session_secret_key`
  - `smtp_password` (if using real SMTP)
- [ ] Update `compose.prod.yml` to use secrets
- [ ] Update backend to read from `/run/secrets/*`
- [ ] Document secret creation process in RUNBOOK
- [ ] Test secret rotation process

**Acceptance Criteria:**
- No `.env` file needed in production
- Secrets loaded from Docker secrets
- Secret rotation documented
- No secrets in logs or error messages

#### 3. Production Tuning (2-3 hours)

Optimize for production workload:

- [ ] **Gunicorn Configuration:**
  - Workers: `(2 * CPU_COUNT) + 1`
  - Worker class: `uvicorn.workers.UvicornWorker`
  - Timeout: 30s
  - Graceful timeout: 30s
  - Keepalive: 5s
- [ ] **PostgreSQL Connection Pooling:**
  - Pool size: 20
  - Max overflow: 10
  - Pool recycle: 3600s
  - Pool pre-ping: true
- [ ] **Redis Configuration:**
  - Maxmemory: 256mb
  - Maxmemory-policy: allkeys-lru
  - Connection pool size: 10
- [ ] **Resource Limits:**
  - Backend: 1GB memory, 1 CPU
  - Frontend: 256MB memory, 0.5 CPU
  - PostgreSQL: 2GB memory, 1 CPU
  - Redis: 512MB memory, 0.5 CPU
- [ ] Test under load (basic smoke test)

**Acceptance Criteria:**
- System stable under basic load
- Resource limits configured
- Connection pools sized appropriately
- No connection exhaustion

#### 4. Deploy & Verify (2-3 hours)

Deploy to VPS and verify functionality:

- [ ] Deploy to VPS (initial deployment)
- [ ] Configure DNS for `rutabagel.com`
- [ ] Verify TLS certificate issued
- [ ] Run smoke tests:
  - Health check (`/healthz`)
  - Magic link flow end-to-end
  - WebAuthn registration
  - Session management
  - CSRF protection
  - Rate limiting
- [ ] Verify monitoring/logging working
- [ ] Document deployment process

**Acceptance Criteria:**
- Production system accessible at `https://rutabagel.com`
- All smoke tests pass
- TLS certificate valid
- Logs visible and structured
- Deployment documented

---

## Phase 4: Testing & CI (Optional)

**Status:** 🔮 Future
**Estimated Effort:** 6-8 hours
**Priority:** Medium - Recommended but not blocking

### Tasks

- [ ] Set up GitHub Actions workflow
- [ ] Add CI jobs:
  - Backend tests (pytest)
  - Frontend tests (vitest)
  - Linting (ruff, mypy, ESLint)
  - Security audit (bandit, npm audit)
  - Migration check (alembic check)
  - Docker image build
- [ ] Add branch protection rules
- [ ] Configure automatic preview deployments (optional)

---

## Phase 5: Observability & Operations (Optional)

**Status:** 🔮 Future
**Estimated Effort:** 8-12 hours
**Priority:** Low - Nice to have

### Tasks

- [ ] Set up nightly database backups
- [ ] Test backup restore process
- [ ] Configure log aggregation (if needed)
- [ ] Set up basic monitoring/alerting
- [ ] Document operational procedures:
  - Deployment process
  - Rollback procedure
  - Backup/restore
  - Secret rotation
  - Scaling guidelines

---

## Feature Development Roadmap

**Status:** 🔮 After Phase 3
**Priority:** Blocked by production deployment

Once production infrastructure is deployed, begin feature development:

### 1. Program Management (2-3 weeks)

Build workout program creation and management:

- [ ] Exercise library (name, muscle group, equipment, instructions)
- [ ] Program builder (collections of exercises with sets/reps/rest)
- [ ] Workout templates (reusable programs)
- [ ] Program sharing and community templates
- [ ] Program versioning and editing

### 2. Workout Logging (2-3 weeks)

Enable users to log workouts:

- [ ] Start workout from program
- [ ] Log sets (reps, weight, RPE, notes)
- [ ] Rest timer between sets
- [ ] Workout history view
- [ ] Offline support with sync (PWA)

### 3. Analytics & Insights (3-4 weeks)

Provide data-driven insights:

- [ ] Progress charts (weight, volume, frequency over time)
- [ ] Personal records (PRs) tracking
- [ ] Muscle group balance analysis
- [ ] Volume tracking (sets per muscle group per week)
- [ ] Predictive insights:
  - Estimated 1RM calculations
  - Deload recommendations
  - Performance trends

### 4. Integration & Correlation (2-3 weeks)

Connect external data sources:

- [ ] Sleep tracking integration
- [ ] Nutrition logging
- [ ] Correlation analysis (sleep quality vs performance)
- [ ] Readiness scores
- [ ] Recovery recommendations

---

## Technical Debt & Improvements

**Ongoing improvements to consider:**

### High Priority

- [ ] OpenAPI client generation for frontend (type-safe API calls)
- [ ] Add integration tests (E2E auth flows)
- [ ] Performance testing (load testing with Locust/k6)

### Medium Priority

- [ ] Add frontend tests (vitest component tests)
- [ ] Improve error handling (user-friendly messages)
- [ ] Add API rate limit headers (X-RateLimit-*)
- [ ] Session device fingerprinting (additional security)

### Low Priority

- [ ] GraphQL API (if REST becomes limiting)
- [ ] Real-time features (WebSocket for live updates)
- [ ] Admin dashboard UI (currently API-only)
- [ ] Multi-language support (i18n)

---

## Decision Log

Key architectural decisions and their rationale:

### API Versioning Strategy (2025-10-29)

**Decision:** Directory-based versioning (`app/api/v1/`)
**Rationale:**
- Supports running multiple versions simultaneously
- Clear separation for backward compatibility
- Easier deprecation during transitions
- Better than prefix-based for production

**Implementation:** Commit `b5ebbcb`

### Documentation Consolidation (2025-10-29)

**Decision:** Single ROADMAP.md for outstanding work, CHANGELOG.md for history
**Rationale:**
- Three overlapping roadmap documents caused confusion
- Status misalignment between documents
- Forward-looking roadmap should only show outstanding work
- Historical reference separate for context

---

## How to Use This Document

**For Contributors:**
1. Check current phase tasks
2. Pick an unassigned task
3. Mark task as started (comment on task or PR)
4. Complete work with tests
5. Update this document when done

**For Project Planning:**
1. Review current phase progress
2. Estimate remaining effort
3. Plan next phase start date
4. Add new tasks as needed

**For Updates:**
- ✅ Complete tasks by checking the checkbox
- 🔄 Update status when starting new phase
- 📝 Add new tasks as requirements emerge
- 🗑️ Remove completed phases (move to CHANGELOG.md)

---

**Next Milestone:** Deploy to production (Phase 3 completion)
**Next Review:** After Phase 3 deployment
