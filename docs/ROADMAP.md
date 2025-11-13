# FitFolio Roadmap

**Last Updated:** 2025-11-06 **Current Phase:** Phase 3A.5 - Test Coverage Improvement

This document tracks **outstanding work only**. For completed work history, see
[CHANGELOG.md](CHANGELOG.md).

---

## 🎯 Immediate Next Steps

**Critical path to production deployment:**

**BLOCKING ISSUE:** Test coverage at 41% - must reach 85% before production deployment.

### Phase 3A: CI/CD Pipeline ✅ COMPLETE

**Completed:** 2025-11-06 (see
[CHANGELOG.md](CHANGELOG.md#2025-11-06---cicd-pipeline--security-hardening-complete))

Full GitHub Actions CI/CD pipeline with comprehensive quality gates:

- ✅ Backend tests with PostgreSQL, Redis, MailHog services (138 tests)
- ✅ Backend linting (ruff, mypy)
- ✅ Backend security (bandit, pip-audit)
- ✅ Backend migration validation (alembic check)
- ✅ Frontend linting (ESLint, Prettier)
- ✅ Frontend build validation
- ✅ Frontend security audit (npm audit)
- ✅ CodeQL analysis (Python + JavaScript/TypeScript)
- ✅ Dependency review (blocks vulnerable deps in PRs)
- ✅ Commit verification (warning mode)

**Pipeline Features:**

- Parallel job execution with optimal caching
- Concurrency control (cancel outdated runs)
- Service containers for testing
- Coverage artifact uploads
- Security scanning with no shortcuts

### Phase 3A.5: Test Coverage Improvement 🚨 BLOCKING (Next - 8-12 hours)

**Priority:** CRITICAL - Must complete before production deployment **Current
Coverage:** 41.29% (453/1097 lines covered) **Target Coverage:** 85% minimum **Estimated
Effort:** 8-12 hours

**Why This Blocks Production:**

- 59% of code is untested - unacceptable production risk
- Critical modules have dangerously low coverage:
  - `app/api/deps.py` - 34% (dependency injection, auth)
  - `app/api/v1/admin.py` - 38% (admin audit endpoints)
  - Core modules likely under-tested
- CI/CD pipeline needs coverage enforcement
- Untested code paths are potential security vulnerabilities
- Production bugs are 10-100x more expensive than test failures

**Tasks:**

1. **Add Coverage Threshold to CI** (30 minutes)
   - Add `--cov-fail-under=85` to pytest in CI workflow
   - Block PRs that drop below coverage threshold
   - Add coverage badge to README
   - Document coverage requirements in contributing guide

2. **Identify Coverage Gaps** (1 hour)
   - Generate detailed coverage report by module
   - Prioritize by risk: auth > admin > core > middleware > routes
   - Create coverage improvement task list
   - Identify untested error paths and edge cases

3. **Test Critical Modules** (4-6 hours)
   - **app/api/deps.py** (34%) - Dependency injection, auth checks
   - **app/api/v1/admin.py** (38%) - Admin audit query endpoints
   - **app/core/webauthn.py** - WebAuthn error handling
   - **app/core/email.py** - Email send failures, SMTP errors
   - **app/middleware/csrf.py** - Edge cases, invalid tokens
   - **app/middleware/rate_limit.py** - Redis failures, limit edge cases

4. **Test Error Paths & Edge Cases** (2-3 hours)
   - Database connection failures and timeouts
   - Redis connection failures
   - Invalid input handling (malformed data, injections)
   - Email send failures (SMTP down, invalid addresses)
   - WebAuthn errors (invalid credentials, replays)
   - Concurrent request handling

5. **Test Integration Flows** (2-3 hours)
   - Complete user journey: registration → verification → login → logout
   - Session rotation edge cases (concurrent requests)
   - Account lockout recovery flows
   - Concurrent session management
   - Multi-device scenarios

**Acceptance Criteria:**

- ✅ Overall backend coverage ≥85%
- ✅ No critical module (auth, admin, core) below 80%
- ✅ CI enforces coverage threshold (PRs fail if below 85%)
- ✅ All error paths have test coverage
- ✅ Coverage badge added to README
- ✅ Coverage report generated in CI artifacts

**Modules Requiring Immediate Attention:** | Module | Current | Target | Priority |
|--------|---------|--------|----------| | app/api/deps.py | 34% | 85% | CRITICAL | |
app/api/v1/admin.py | 38% | 85% | CRITICAL | | app/core/webauthn.py | Unknown | 85% |
HIGH | | app/core/email.py | Unknown | 85% | HIGH | | app/middleware/\* | Unknown | 85%
| MEDIUM |

### Phase 3B: Production Deployment (After Coverage - 6-8 hours)

Now that CI/CD is complete, focus on production deployment:

**Remaining Tasks:**

1. **Docker Secrets Management** (1-2 hours)
   - Set up Docker secrets in compose.prod.yml
   - Update backend to read from `/run/secrets/*` files
   - Document required secrets (JWT_SECRET, DB passwords, SMTP credentials)
   - Test secret injection locally
   - Create secrets on production VPS

2. **Production SMTP Configuration** (1 hour)
   - Choose email service (SendGrid/AWS SES/Mailgun)
   - Get API credentials
   - Add as Docker secrets
   - Update backend email configuration
   - Test email delivery

3. **Production Docker Images** (1-2 hours)
   - Create optimized production Dockerfile for frontend (multi-stage build)
   - Configure Vite production build settings
   - Build and test images locally
   - Push to GitHub Container Registry

4. **Deploy to Production VPS** (2-3 hours)
   - Pull production images from registry
   - Deploy using `compose.prod.yml`
   - Configure DNS for production domain
   - Verify TLS certificate issuance
   - Run smoke tests

5. **Security Headers & Validation** (1 hour)
   - Configure Traefik middleware for security headers
   - Verify all security features working
   - Test secret rotation process
   - Document deployment process

**After these tasks, Phase 3 will be complete!**

---

## Phase 3: Production Deployment

**Status:** 🔄 In Progress **Estimated Effort:** 12-16 hours (includes CI/CD setup)
**Target:** Deploy production-ready system to utility node (existing VPS)

### Prerequisites

- ✅ All Phase 2B security work complete
- ✅ 138 tests passing (100% pass rate)
- ✅ API versioning implemented
- ✅ Pre-commit hooks enforcing quality
- ✅ Traefik integration tested in dev
- ✅ CI/CD pipeline complete (Phase 3A)
- ⏳ Test coverage ≥85% (Phase 3A.5 - IN PROGRESS)

### Tasks

**Phase 3A: CI/CD & Build ✅ COMPLETE (2025-11-06)**

#### 1. GitHub Actions CI/CD ✅ COMPLETE

**Status:** Complete **Time Spent:** ~6 hours

Comprehensive CI/CD pipeline implemented with all quality gates:

- ✅ **CI Pipeline for Pull Requests:**
  - ✅ Backend tests (138 tests, 100% passing)
  - ✅ Frontend tests (vitest with continue-on-error)
  - ✅ Linting (ruff, mypy, ESLint, prettier)
  - ✅ Security scans (bandit, pip-audit, npm audit)
  - ✅ Migration check (alembic check)
  - ✅ CodeQL analysis (Python + JavaScript/TypeScript)
  - ✅ Dependency review (blocks vulnerable deps)
  - ✅ Commit verification (warning mode)

- ⏳ **CD Pipeline for Main Branch:**
  - [ ] Build backend Docker image (pending - will add in Phase 3B)
  - [ ] Build frontend Docker image (pending - will add in Phase 3B)
  - [ ] Push images to GitHub Container Registry
  - [ ] Tag images with commit SHA and 'latest'

- ⏳ **Secrets Management:**
  - [ ] Set up Docker secrets in compose.prod.yml (Phase 3B Task 1)
  - [ ] Update backend to read from `/run/secrets/*` files
  - [ ] Document required secrets

- ⏳ **Production Frontend Dockerfile:**
  - [ ] Create multi-stage build (Phase 3B Task 3)

**Acceptance Criteria:**

- ✅ PR builds run all tests and quality checks
- ✅ All jobs passing with no shortcuts
- ✅ Security scanning comprehensive
- ⏳ Image building (moved to Phase 3B)

**Phase 3B: Production Setup (after CI/CD)**

#### 2. Traefik Integration (2-3 hours) ✅ PARTIAL

**Decision:** Use existing Traefik instance (already running UniFi + Vaultwarden)

**Completed:**

- ✅ Update `compose.dev.yml` with Traefik labels
- ✅ Update `compose.prod.yml` with Traefik labels:
  - Backend routing: `Host(fitfolio.rutabagel.com) && PathPrefix(/api)`
  - Frontend routing: `Host(fitfolio.rutabagel.com)` (lower priority)
  - TLS configuration
- ✅ Connect FitFolio services to `traefik-public` network
- ✅ Network isolation (traefik-public + default)
- ✅ Add missing environment variables (EMAIL_SENDER, JWT_SECRET, CORS_ORIGINS)
- ✅ Add restart policies and healthchecks
- ✅ Test in development at `https://fitfolio.dev.rutabagel.com`
- ✅ Verify routing (frontend, backend, health checks)
- ✅ Add API root endpoint (`/api`) for version discovery

**Remaining:**

- [ ] Configure security headers middleware (if not already in Traefik):
  - HSTS (Strict-Transport-Security)
  - CSP (Content-Security-Policy)
  - X-Frame-Options, X-Content-Type-Options
- [ ] Deploy to production VPS
- [ ] Verify automatic TLS certificate issuance for production domain
- [ ] Configure DNS for production domain
- [ ] Verify no CORS errors in production

**Architecture:** Traefik handles reverse proxy + TLS, Nginx stays in frontend container
for static file serving

**Reference:** See [docs/REVERSE_PROXY_ANALYSIS.md](REVERSE_PROXY_ANALYSIS.md) for
detailed comparison

**Acceptance Criteria:**

- ✅ HTTPS works on dev domain (`fitfolio.dev.rutabagel.com`)
- ✅ Backend accessible at `/api/v1/*`
- ✅ Frontend serves at `/` (all other routes)
- [ ] Production HTTPS works on `fitfolio.rutabagel.com`
- [ ] TLS certificate auto-issued via Let's Encrypt (production)
- [ ] Security headers present in responses
- [ ] HTTP redirects to HTTPS (if not already configured in Traefik)
- [ ] No CORS errors in production

#### 3. Production SMTP Configuration (1 hour)

Configure real email service for production:

- [ ] Choose email service (SendGrid/AWS SES/Mailgun)
- [ ] Create account and get API credentials
- [ ] Add SMTP credentials to Docker secrets
- [ ] Update backend email configuration for production SMTP
- [ ] Test email delivery in production
- [ ] Update compose.prod.yml to remove Mailpit, add SMTP config

**Acceptance Criteria:**

- Magic link emails delivered successfully
- Email verification emails delivered
- No Mailpit in production
- SMTP credentials secured via Docker secrets
- Email delivery monitored/logged

**Note:** Basic secrets management setup happens in Task 1 (CI/CD)

#### 4. Production Tuning (2-3 hours)

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

#### 5. Deploy & Verify (2-3 hours)

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

## Phase 4: Observability & Operations (Optional)

**Status:** 🔮 Future **Estimated Effort:** 8-12 hours **Priority:** Low - Nice to have

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

**Status:** 🔮 After Phase 3 **Priority:** Blocked by production deployment

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

- [ ] **Frontend build optimization** - Configure production build settings
  - [ ] Optimize Vite build configuration
  - [ ] Add bundle size analysis
  - [ ] Configure asset optimization (images, fonts)
  - [ ] Set up production environment variables
  - [ ] Create production Dockerfile for frontend (currently uses dev server in prod
        compose)
- [ ] **Production SMTP configuration** - Replace Mailpit with real email service
  - [ ] Configure SendGrid/AWS SES/Mailgun credentials
  - [ ] Update backend email configuration
  - [ ] Test email delivery in production
  - [ ] Document email service setup
- [ ] OpenAPI client generation for frontend (type-safe API calls)
- [ ] Add integration tests (E2E auth flows)
- [ ] Performance testing (load testing with Locust/k6)

### Medium Priority

- [ ] **Deprecate FastAPI `on_event` decorators** - Migrate to lifespan context manager
  - Current deprecation warnings in tests
  - See: https://fastapi.tiangolo.com/advanced/events/
- [ ] **Fix resource warnings in tests** - Unclosed socket/transport warnings
  - Redis connection cleanup
  - Test fixture improvements
- [ ] Add frontend tests (vitest component tests)
- [ ] Improve error handling (user-friendly messages)
- [ ] Add API rate limit headers (X-RateLimit-\*)
- [ ] Session device fingerprinting (additional security)
- [ ] **Frontend authentication state management** - Implement proper auth state
  - [ ] Context provider for auth state
  - [ ] Protected route components
  - [ ] Session persistence across refreshes
  - [ ] Logout handling

### Low Priority

- [ ] GraphQL API (if REST becomes limiting)
- [ ] Real-time features (WebSocket for live updates)
- [ ] Admin dashboard UI (currently API-only)
- [ ] Multi-language support (i18n)
- [ ] **Staging environment** - Add compose.staging.yml for testing
  - Similar to prod but with staging domain
  - Could use for pre-production validation

---

## Architecture Decision Records (ADRs)

Key architectural decisions are documented as ADRs in [`docs/adr/`](adr/).

**Active Decisions:**

- [ADR-0001: Directory-Based API Versioning](adr/0001-directory-based-api-versioning.md)
  (2025-10-29)
- [ADR-0002: Traefik Reverse Proxy Integration](adr/0002-traefik-reverse-proxy-integration.md)
  (2025-10-31)
- [ADR-0003: Passwordless Authentication Strategy](adr/0003-passwordless-authentication-strategy.md)
  (2025-10-26)
- [ADR-0004: Opaque Server-Side Sessions](adr/0004-opaque-server-side-sessions.md)
  (2025-10-26)

See [ADR Index](adr/README.md) for full list and guidelines on creating new ADRs.

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

**Next Milestone:** Deploy to production (Phase 3 completion) **Next Review:** After
Phase 3 deployment
