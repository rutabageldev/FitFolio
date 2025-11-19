# FitFolio Roadmap

**Last Updated:** 2025-11-17 **Current Status:** Production Deployment (Phase 3B)

This document tracks **outstanding work only**. For completed work, see
[CHANGELOG.md](CHANGELOG.md).

---

## Current Phase: Production Deployment

### Phase 3B: Production Setup (In Progress)

**Status:** Docker secrets migration complete; automated staging deployments live and
green

#### Completed ✅

- ✅ **CI/CD Pipeline** (Phase 3A)
  - GitHub Actions workflow with all quality gates
  - Backend tests (397 passing, 97.81% coverage)
  - Frontend linting and build validation
  - Security scanning (CodeQL, bandit, npm audit)
  - Coverage enforcement (85% minimum)
- ✅ **Test Coverage** (Phase 3A.5)
  - Coverage improved from 41% to 97.81%
  - All critical modules above 85% coverage
  - Handler-level tests for all auth endpoints
- ✅ **Docker Secrets** (Phase 3B Task 1)
  - Production secrets management implemented
  - Development secrets for dev/prod parity
  - Documentation for both environments
- ✅ **Traefik Integration** (Partial)
  - Development domain working (`fitfolio.dev.rutabagel.com`)
  - Routing configuration complete
  - Network isolation configured
- ✅ **Staging Environment & CD**
  - Automated deploys to `fitfolio-staging.rutabagel.com` after CI + image build
  - Immutable image tags (`sha-<12>`) verified in GHCR
  - One-off migration service runs before app traffic
  - Health/TLS checks and smoke tests post-deploy
  - Docs: `docs/deployment/STAGING.md`, workflow: `cd-staging-promote.yml`

#### Remaining Tasks

**1. Production Deployment** (2-3 hours)

- [ ] Deploy to VPS using `compose.prod.yml`
- [ ] Configure DNS for production domain (`fitfolio.rutabagel.com`)
- [ ] Create Docker secrets on production server
- [ ] Verify TLS certificate issuance
- [ ] Run smoke tests

**2. Production SMTP Configuration** (1 hour)

- [ ] Choose email service (SendGrid/AWS SES/Mailgun)
- [ ] Configure SMTP credentials as Docker secrets
- [ ] Update email configuration in production
- [ ] Test email delivery

**3. Security Validation** (1 hour)

- [ ] Verify security headers (HSTS, CSP, etc.)
- [ ] Test CSRF protection in production
- [ ] Test rate limiting in production
- [ ] Verify session rotation working

**4. Monitoring & Documentation** (1 hour)

- [ ] Verify structured logging working
- [ ] Document deployment process
- [ ] Document secret rotation process
- [ ] Create operations runbook

---

## Future Phases

### Phase 4: Observability & Operations (Optional)

**Priority:** Low - Nice to have

- [ ] Set up database backups (nightly)
- [ ] Test backup restore process
- [ ] Configure log aggregation (if needed)
- [ ] Set up monitoring/alerting
- [ ] Document operational procedures

### Phase 5: Feature Development

**Status:** Blocked until production is deployed

#### 1. Program Management (2-3 weeks)

- [ ] Exercise library
- [ ] Program builder (sets/reps/rest)
- [ ] Workout templates
- [ ] Program sharing

#### 2. Workout Logging (2-3 weeks)

- [ ] Start workout from program
- [ ] Log sets with weight/reps/RPE
- [ ] Rest timer
- [ ] Workout history
- [ ] Offline support (PWA)

#### 3. Analytics & Insights (3-4 weeks)

- [ ] Progress charts
- [ ] Personal records tracking
- [ ] Volume tracking
- [ ] Performance trends
- [ ] Estimated 1RM calculations

#### 4. Integration & Correlation (2-3 weeks)

- [ ] Sleep tracking integration
- [ ] Nutrition logging
- [ ] Correlation analysis
- [ ] Readiness scores

---

## Technical Debt

### High Priority

- [ ] Frontend production build optimization
  - [ ] Optimize Vite configuration
  - [ ] Bundle size analysis
  - [ ] Asset optimization
- [ ] OpenAPI client generation for frontend
- [ ] E2E integration tests
- [ ] Load testing (Locust/k6)

### Medium Priority

- [ ] Migrate FastAPI `on_event` to lifespan context manager
- [ ] Fix resource warnings in tests
- [ ] Frontend component tests (vitest)
- [ ] API rate limit headers (X-RateLimit-\*)
- [ ] Frontend auth state management

### Low Priority

- [ ] GraphQL API (if REST becomes limiting)
- [ ] Real-time features (WebSocket)
- [ ] Admin dashboard UI
- [ ] Multi-language support (i18n)

---

## Architecture Decisions

Key decisions documented in [`docs/adr/`](adr/):

- [ADR-0001: Directory-Based API Versioning](adr/0001-directory-based-api-versioning.md)
- [ADR-0002: Traefik Reverse Proxy](adr/0002-traefik-reverse-proxy-integration.md)
- [ADR-0003: Passwordless Authentication](adr/0003-passwordless-authentication-strategy.md)
- [ADR-0004: Opaque Server-Side Sessions](adr/0004-opaque-server-side-sessions.md)

See [ADR Index](adr/README.md) for full list.

---

## How to Use This Document

**For Contributors:**

1. Check current phase tasks
2. Pick an unassigned task
3. Complete work with tests
4. Update this document and CHANGELOG.md

**For Updates:**

- ✅ Check off completed tasks
- 🗑️ Move completed phases to CHANGELOG.md
- 📝 Add new tasks as requirements emerge

---

**Next Milestone:** Production deployment complete **Next Review:** After first
production deployment
