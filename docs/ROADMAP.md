# FitFolio Roadmap

**Last Updated:** 2025-10-31
**Current Phase:** Phase 3 - Production Deployment

This document tracks **outstanding work only**. For completed work history, see [CHANGELOG.md](CHANGELOG.md).

---

## 🎯 Immediate Next Steps

**Critical path to production deployment:**

### Phase 3A: CI/CD Pipeline (MUST DO FIRST - 4-6 hours)

You're on an isolated dev node and need CI/CD to build and deploy to production.

1. **Set up GitHub Actions workflow** (2-3 hours)
   - Add CI workflow for PRs (tests, linting, security scans)
   - Add CD workflow for main branch (build images, push to registry)
   - Configure Docker build and push to GitHub Container Registry
   - Add GitHub Actions secrets (Docker registry, etc.)

2. **Docker Secrets Management** (1 hour)
   - Set up Docker secrets in compose.prod.yml
   - Update backend to read from `/run/secrets/*` files
   - Document required secrets (JWT_SECRET, DB passwords, etc.)
   - Test secret injection locally

3. **Build Production Docker Images** (1-2 hours)
   - Create optimized production Dockerfile for frontend
   - Configure Vite production build settings
   - Test image builds in CI
   - Verify images pushed to registry

4. **Deployment Strategy** (1 hour)
   - Document manual deployment process (pull images on VPS)
   - OR set up automated deployment (GitHub Actions → SSH → VPS)
   - Consider: Watchtower for auto-updates vs. manual control

**Why CI/CD First?**
- Currently on isolated dev node - can't ship to prod without it
- Need automated image building for production
- Secrets management must be in place before deployment
- Quality gates before deployment
- Repeatable deployment process

### Phase 3B: Production Deployment (After CI/CD - 3-4 hours)

Once CI/CD can build and ship images and secrets are configured:

5. **Configure Production SMTP** (1 hour)
   - Choose email service (SendGrid/AWS SES/Mailgun)
   - Add credentials as Docker secrets
   - Update backend email configuration
   - Test email delivery

6. **Deploy to Production VPS** (1-2 hours)
   - Create Docker secrets files on VPS
   - Pull production images from registry
   - Deploy using `compose.prod.yml`
   - Configure DNS for production domain
   - Verify TLS certificate issuance

7. **Security Headers & Validation** (1 hour)
   - Configure Traefik middleware for security headers
   - Run smoke tests on production
   - Verify all acceptance criteria met
   - Test secret rotation process

**After these tasks, Phase 3 will be complete!**

---

## Phase 3: Production Deployment

**Status:** 🔄 In Progress
**Estimated Effort:** 12-16 hours (includes CI/CD setup)
**Target:** Deploy production-ready system to utility node (existing VPS)

### Prerequisites

- ✅ All Phase 2B security work complete
- ✅ 138 tests passing (updated from 93)
- ✅ API versioning implemented
- ✅ Pre-commit hooks enforcing quality
- ✅ Traefik integration tested in dev

### Tasks

**Phase 3A: CI/CD & Build (4-6 hours) - REQUIRED FIRST**

#### 1. GitHub Actions CI/CD (4-6 hours) 🚨 BLOCKING

**Status:** Not Started
**Priority:** CRITICAL - Blocks production deployment

Set up automated build and deployment pipeline:

- [ ] **CI Pipeline for Pull Requests:**
  - [ ] Backend tests (pytest with coverage)
  - [ ] Frontend tests (vitest - if/when added)
  - [ ] Linting (ruff, mypy, ESLint, prettier)
  - [ ] Security scans (bandit, npm audit)
  - [ ] Migration check (alembic check)
  - [ ] Pre-commit hooks validation

- [ ] **CD Pipeline for Main Branch:**
  - [ ] Build backend Docker image
  - [ ] Build frontend Docker image (production optimized)
  - [ ] Push images to GitHub Container Registry (ghcr.io)
  - [ ] Tag images with commit SHA and 'latest'

- [ ] **Secrets Management:**
  - [ ] Configure GitHub Actions secrets for sensitive values
  - [ ] Set up Docker secrets in compose.prod.yml
  - [ ] Update backend to read from `/run/secrets/*` files
  - [ ] Document which secrets are needed (JWT_SECRET, DATABASE_PASSWORD, etc.)
  - [ ] Test secret injection locally

- [ ] **Deployment Strategy:**
  - [ ] Document manual deployment (pull images on VPS)
  - [ ] OR automate deployment (GitHub Actions → SSH → VPS)
  - [ ] Consider: Watchtower for auto-updates vs. manual control

- [ ] **Production Frontend Dockerfile:**
  - [ ] Multi-stage build (node build → nginx serve)
  - [ ] Optimize Vite build settings
  - [ ] Configure nginx for SPA routing
  - [ ] Test image builds locally

**Acceptance Criteria:**
- PR builds run all tests and quality checks
- Main branch builds and pushes production images
- Images available in GitHub Container Registry
- Deployment process documented
- Can pull and run images on any Docker host

**Why This Blocks Everything:**
- Currently on isolated dev node
- No way to build production images without CI
- Can't deploy to prod VPS without images in registry

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

**Architecture:** Traefik handles reverse proxy + TLS, Nginx stays in frontend container for static file serving

**Reference:** See [docs/REVERSE_PROXY_ANALYSIS.md](REVERSE_PROXY_ANALYSIS.md) for detailed comparison

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

- [ ] **Frontend build optimization** - Configure production build settings
  - [ ] Optimize Vite build configuration
  - [ ] Add bundle size analysis
  - [ ] Configure asset optimization (images, fonts)
  - [ ] Set up production environment variables
  - [ ] Create production Dockerfile for frontend (currently uses dev server in prod compose)
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
- [ ] Add API rate limit headers (X-RateLimit-*)
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

## Decision Log

Key architectural decisions and their rationale:

### Traefik Integration Strategy (2025-10-31)

**Decision:** Use existing Traefik instance for both dev and prod, configure via Docker labels
**Rationale:**
- Traefik already running on utility node (UniFi, Vaultwarden)
- Automatic Let's Encrypt certificate management
- No need for Nginx reverse proxy layer
- Declarative configuration via labels
- Can test exact production routing in dev environment

**Implementation:** Commit `b688b8c`

**Benefits:**
- Zero-downtime deployments (Traefik handles routing)
- Automatic SSL certificate renewal
- Consistent configuration between dev/prod
- Infrastructure already proven reliable

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
