# FitFolio Architecture Assessment

**Date:** 2025-10-27
**Status:** Phase 2 (Auth MVP) - In Progress
**Overall Rating:** 7.5/10 - Strong foundation with clear gaps to address

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Strengths](#architecture-strengths)
3. [Critical Gaps & Weaknesses](#critical-gaps--weaknesses)
4. [Technology Stack Assessment](#technology-stack-assessment)
5. [Architectural Decisions to Make](#architectural-decisions-to-make)
6. [Recommended Additions](#recommended-additions)
7. [Phase-by-Phase Action Plan](#phase-by-phase-action-plan)
8. [Detailed Ratings by Category](#detailed-ratings-by-category)
9. [Open Questions](#open-questions)

---

## Executive Summary

FitFolio's target architecture is **well-designed for a personal project** with a strong foundation in modern best practices. It strikes a good balance between simplicity and production-readiness.

**Key Strengths:**
- Security-first authentication design (passwordless + WebAuthn)
- Excellent observability infrastructure (structlog + OpenTelemetry)
- Solid database schema with proper indexing
- Outstanding developer experience (dev container, hot reload, Makefile)

**Critical Gaps (Blocking Production):**
1. WebAuthn challenge storage vulnerability (client-side, can be modified)
2. Missing CSRF protection on POST endpoints
3. No rate limiting on auth endpoints

**Recommendation:** Address critical security gaps in Phase 2 completion, then proceed with Phase 3 (Traefik + TLS + secrets management).

---

## Architecture Strengths

### 1. Security-First Design ⭐⭐⭐⭐⭐

**Passwordless Authentication:**
- Magic link (email-based, single-use, 15-min TTL)
- WebAuthn/Passkeys (phishing-resistant, modern)
- No password complexity/reset burden

**Session Management:**
- Opaque tokens (SHA-256 hashed, never plaintext)
- HttpOnly cookies (XSS protection)
- 14-day TTL with rotation infrastructure
- Server-side storage in PostgreSQL

**Routing Strategy:**
- Single host (`rutabagel.com`) eliminates CORS complexity in production
- Backend at `/api` with prefix stripping via Traefik

**Assessment:** Enterprise-grade authentication architecture. Excellent foundation.

---

### 2. Observability Infrastructure ⭐⭐⭐⭐

**Logging:**
- Structured JSON logs (structlog)
- Request ID correlation across services
- Proper log levels (DEBUG in dev, INFO in prod)

**Tracing:**
- OpenTelemetry instrumentation for FastAPI, Psycopg, Requests
- Ready for OTLP collector integration
- Distributed tracing foundation in place

**Monitoring:**
- Health checks configured (`/healthz`)
- Docker health check probes
- Ready for metrics export

**Gap:** No collectors/dashboards deployed yet (planned for Phase 5).

**Assessment:** Infrastructure is correctly implemented from day one. Just needs wiring to observability backend.

---

### 3. Database Design ⭐⭐⭐⭐⭐

**Schema:**
- Well-normalized (4 tables: users, sessions, webauthn_credentials, login_events)
- Proper foreign keys with CASCADE for data integrity
- JSONB for flexible event metadata
- INET type for IP addresses (native validation)

**Indexing Strategy:**
- Unique constraint on `lower(email)` (case-insensitive)
- Composite index on `(user_id, expires_at)` for session queries
- Indexes on `(user_id, created_at)` and `(event_type, created_at)` for audit queries

**Migrations:**
- Alembic with autogeneration
- Proper naming conventions configured
- Version control for schema changes

**Assessment:** Production-ready schema design. No changes needed for MVP.

---

### 4. Developer Experience ⭐⭐⭐⭐⭐

**Local Development:**
- Dev Container with consistent environment
- Hot reload for backend (uvicorn `--reload`)
- Hot reload for frontend (Vite HMR)
- Mailpit for email testing (no external SMTP needed)

**Tooling:**
- Makefile with 20+ commands (`make up`, `make logs`, `make migrate`, etc.)
- Pre-commit hooks (ruff, mypy, bandit, eslint, prettier)
- Clear documentation (RUNBOOK.md, fitfolio_infra_plan.md)

**Quality Enforcement:**
- Automated linting/formatting on commit
- Type checking (mypy for Python, TypeScript for frontend)
- Security scanning (bandit, pip-audit, detect-secrets)

**Assessment:** Developer ergonomics are top-tier. Excellent for solo or small team.

---

### 5. Containerization Strategy ⭐⭐⭐⭐

**Docker Setup:**
- Multi-stage builds for production (smaller images, security)
- Separate dev/prod Dockerfiles
- Health checks properly configured
- Service dependencies handled (`depends_on` + health conditions)

**Compose Files:**
- `compose.dev.yml` - 4 services (backend, frontend, db, mailpit)
- `compose.prod.yml` - 3 services (backend, frontend, db)
- Volume management for data persistence

**Assessment:** Containerization is production-aware from the start. Good separation of dev/prod concerns.

---

## Critical Gaps & Weaknesses

### 🔴 1. WebAuthn Challenge Storage (CRITICAL - BLOCKING PRODUCTION)

**Current State:**
Challenges are returned to the frontend in API responses (`/auth/webauthn/register/start`, `/auth/webauthn/authenticate/start`).

**Security Risk:**
Client can modify the challenge before submitting it to `/finish` endpoint, undermining the entire WebAuthn security model. This allows potential credential forgery.

**Required Fix:**
1. Add Redis to stack (or use encrypted session storage)
2. Store challenges server-side with short TTL (30-60 seconds)
3. Return only an opaque challenge ID to client
4. Verify stored challenge matches credential response on `/finish`

**Impact:** 🔴 **BLOCKS PRODUCTION DEPLOYMENT**

**Effort:** 2-3 hours (add Redis + refactor 4 endpoints)

**Priority:** P0 - Fix in Phase 2 completion

---

### 🔴 2. Missing CSRF Protection (CRITICAL - BLOCKING PRODUCTION)

**Current State:**
POST endpoints lack CSRF token validation. Relies solely on SameSite=Lax cookies.

**Security Risk:**
State-changing operations (login, logout, credential registration) vulnerable to CSRF if user visits malicious site while authenticated. SameSite=Lax provides partial protection but not sufficient.

**Required Fix:**
Implement one of:
- **Double-submit cookie pattern** (stateless, simpler)
- **Synchronizer token pattern** (stateful, more secure)
- Use `fastapi-csrf-protect` library

**Impact:** 🔴 **BLOCKS PRODUCTION DEPLOYMENT**

**Effort:** 1-2 hours

**Priority:** P0 - Fix in Phase 2 completion

**Recommendation:** Double-submit cookie pattern is sufficient for your threat model and easier to implement.

---

### 🟡 3. No Rate Limiting (HIGH PRIORITY)

**Current State:**
Auth endpoints can be hammered without restriction.

**Security Risk:**
- Brute force attacks on magic link/WebAuthn
- Email flooding (DOS via magic link requests)
- Resource exhaustion

**Required Fix:**
1. Add rate limiting middleware (slowapi + Redis backend)
2. Apply to auth endpoints:
   - `/auth/magic-link/start`: 5 requests/min per IP
   - `/auth/webauthn/*/start`: 10 requests/min per IP
   - `/auth/webauthn/*/finish`: 20 requests/min per IP (allow retries)

**Impact:** 🟡 **HIGH priority for production**

**Effort:** 2-3 hours (once Redis is integrated)

**Priority:** P1 - Add in Phase 3

---

### 🟡 4. Session Rotation Dormant (MEDIUM PRIORITY)

**Current State:**
Database has `rotated_at` field, but rotation is never triggered.

**Gap:**
Sessions don't rotate on:
- Privilege escalation events
- Time-based triggers (e.g., every 7 days per `SESSION_ROTATE_DAYS=7` config)

**Required Fix:**
1. Add rotation trigger after WebAuthn credential addition
2. Add time-based rotation check in session validation
3. Issue new token, mark old as rotated, return new cookie

**Impact:** 🟡 **Medium priority**

**Effort:** 1 hour

**Priority:** P2 - Add in Phase 2 completion or early Phase 3

---

### 🟡 5. Secrets Management Gap (PRODUCTION CONCERN)

**Current State:**
`.env` file with plaintext secrets in dev/prod.

**Target Architecture:**
Phase 3 specifies Docker secrets, fitfolio_infra_plan.md mentions Vault.

**Gap:**
Two competing strategies mentioned, no clear decision on which to prioritize.

**Decision Needed:**
- **Docker Secrets** (simpler, single-host, good for your scale)
- **Vault** (complex, overkill for personal project, high operational overhead)

**Recommendation:**
- **Phase 3:** Implement Docker Secrets (sufficient for your needs)
- **Reconsider Vault** only if you hit these triggers:
  - Multiple services needing dynamic secrets
  - Automated secret rotation required
  - Compliance requirements

**Vault Concerns for Personal Project:**
- Requires unseal process on every restart (manual step)
- Another service to monitor/backup
- High learning curve
- Operational overhead outweighs benefits at your scale

**Alternative to Consider:**
- **Doppler** or **Infisical** (SaaS secrets management, less operational burden)
- **SOPS** with age encryption (GitOps-friendly, no runtime service)

**Priority:** P1 - Decide and implement in Phase 3

---

### 🟡 6. Traefik Integration Not Defined (ARCHITECTURAL CLARITY NEEDED)

**Plan:** Traefik for reverse proxy, TLS, `/api` routing.

**Gaps:**
- No Traefik config files in repo yet
- TLS certresolver strategy undefined (Let's Encrypt staging vs. prod)
- Health check aggregation unclear
- Middleware configuration (compression, security headers) not planned
- Current `compose.prod.yml` exposes ports directly (8081, 8082) - will change with Traefik

**Decisions Needed:**
1. **Deployment:** Traefik in Docker Compose or separately?
2. **Configuration:** Static config file vs. dynamic via Docker labels?
3. **TLS:** Let's Encrypt certresolver? Which challenge type (HTTP-01, DNS-01)?
4. **Certificate Storage:** Where to persist `acme.json`?
5. **Dev Testing:** Use mkcert for local TLS testing?

**Recommendation:**
- **Configuration:** Dynamic via Docker labels (easier to maintain per-service)
- **TLS:** Let's Encrypt HTTP-01 challenge (simpler, no DNS API needed)
- **Storage:** Docker volume for `acme.json` + backup to off-host
- **Dev Testing:** Use mkcert for local HTTPS testing before deploying

**Effort:** 4-6 hours first time (learning curve + testing)

**Priority:** P1 - Start in Phase 3

**Next Steps:**
1. Create `traefik/traefik.yml` for static config
2. Create `compose.traefik.yml` for Traefik service
3. Add Docker labels to `compose.prod.yml` for routing
4. Test with Let's Encrypt staging endpoint first

---

### 🟡 7. Redis Not Yet Integrated (BLOCKING FOR CHALLENGE STORAGE)

**Current State:**
Mentioned as planned but no concrete integration.

**Use Cases You Need:**
1. **WebAuthn challenge storage** (15-30 sec TTL) - **CRITICAL**
2. **Rate limiting counters** - **HIGH**
3. **Session caching** (optional, but faster than Postgres) - **MEDIUM**
4. **Magic link token storage** (currently in DB - could move to Redis) - **LOW**

**Decisions Needed:**
1. **Topology:** Single Redis instance or Redis Sentinel/Cluster?
2. **Persistence:** AOF, RDB, or none for ephemeral data?
3. **Eviction Policy:** allkeys-lru (for cache) or volatile-ttl (for TTL-based data)?

**Recommendation:**
- **Phase 2 completion:** Add Redis to `compose.dev.yml`
- **Configuration:**
  - Image: `redis:7-alpine`
  - Persistence: RDB (for rate limit data)
  - Eviction: `maxmemory-policy allkeys-lru`
  - Max Memory: 256MB (sufficient for your scale)
- **Topology:** Single instance (no Sentinel needed for personal project)

**Effort:** 30 min to add to compose files + 2-3 hours to integrate

**Priority:** P0 - Add in Phase 2 completion

---

### 🟠 8. Frontend Architecture Undefined (MAJOR GAP)

**Current State:**
Single `App.jsx` with hardcoded API ping.

**Needed for Phase 2 MVP:**
- **Routing:** React Router? TanStack Router?
- **State Management:** Context API? Zustand? Redux?
- **API Client:** fetch wrapper? Axios? TanStack Query?
- **Form Handling:** React Hook Form? Formik?
- **Error Boundaries:** Not implemented
- **Auth Context:** Not implemented

**Decisions Needed:**
1. **Routing:** Multi-page app or single page with dynamic content?
2. **State Management:** How complex will workout tracking UI be?
3. **UI Framework:** Plain CSS? Tailwind? MUI? shadcn/ui?
4. **Type Safety:** Commit to TypeScript now or stay with JavaScript?

**Recommendations (Backend Dev Friendly):**

**Minimal (Fastest to MVP):**
- Routing: React Router v6 (stable, well-documented)
- State: Context API (built-in, sufficient for auth state)
- API: Native `fetch` with wrapper function
- Forms: Plain React state (add library later if needed)
- Styling: Plain CSS or CSS modules (defer framework decision)

**Moderate (Better DX, Still Simple):**
- Routing: React Router v6
- State: Zustand (simpler than Redux, better than Context for complex state)
- API: TanStack Query (handles caching, loading states, retries automatically)
- Forms: React Hook Form (less boilerplate than Formik)
- Styling: Tailwind CSS (utility-first, fast prototyping)

**Advanced (Overkill for MVP):**
- Full TypeScript (`.tsx` files, strict mode)
- Redux Toolkit (too heavy for auth-only state)
- GraphQL (unnecessary for simple REST API)

**Recommendation for You:**
Start with **Minimal** to unblock UI work, then add libraries as pain points emerge. React Router v6 + Context API + native fetch is sufficient for auth flows.

**Priority:** P1 - Decide in next session (don't need to decide now)

**Note:** Defer detailed frontend decisions until Phase 2 UI work begins. Focus on backend security fixes first.

---

### 🟠 9. Testing Strategy Underspecified (QUALITY CONCERN)

**Plan:** pytest for backend, vitest for frontend, 95% coverage target.

**Gaps:**
- No test structure defined (unit vs. integration vs. E2E boundaries)
- No testing database strategy (fixtures? factory pattern? test DB instance?)
- No mocking strategy for external dependencies (email, WebAuthn)
- CI runs tests but always passes (`|| true` in workflow)

**Decisions Needed:**
1. **Test DB:** Separate test DB instance? In-memory SQLite?
2. **Fixtures:** pytest fixtures or factory_boy?
3. **WebAuthn Testing:** How to mock authenticator?
4. **E2E Testing:** Playwright? Cypress? Or just integration tests?

**Recommendation:**
- **Test DB:** Spin up/tear down test PostgreSQL instance per test session
- **Fixtures:** Use pytest fixtures (simpler, built-in)
- **Mocking:** Mock external deps (aiosmtplib, webauthn challenge generation)
- **E2E:** Defer until post-MVP (manual testing sufficient for MVP)

**Test Structure:**
```
backend/tests/
├── conftest.py          # Fixtures (test DB, test client)
├── test_auth.py         # Auth endpoints (magic link, WebAuthn)
├── test_models.py       # SQLAlchemy models
├── test_security.py     # Token hashing, validation
└── test_session.py      # Session management, rotation
```

**Effort:** 6-8 hours to set up structure + write first tests

**Priority:** P2 - Phase 4

**First Step:** Remove `|| true` from CI workflow once first test passes.

---

### 🟠 10. Database Backup Strategy Vague (OPERATIONAL RISK)

**Phase 5 mentions:** "Nightly DB backups with restore test."

**Gaps:**
- Backup tool undefined (pg_dump? pg_basebackup? Continuous archiving?)
- Storage location undefined (local volume? S3? Backblaze?)
- Retention policy undefined (7 days? 30 days? Point-in-time recovery?)
- Restore testing not automated

**Decisions Needed:**
1. **RPO (Recovery Point Objective):** How much data loss can you tolerate?
2. **RTO (Recovery Time Objective):** How quickly do you need to recover?
3. **Storage Budget:** Cost tolerance for backup storage?

**Recommendation:**

**Simple (Phase 5):**
- Tool: `pg_dump` (full daily backups)
- Schedule: Cron job at 2 AM daily
- Storage: Local volume + rsync to off-host (Backblaze B2, rsync.net)
- Retention: 7 daily + 4 weekly + 3 monthly
- Restore Test: Monthly manual restore to verify

**Better (Post-Phase 5):**
- Tool: pgBackRest or Barman
- Incremental backups + PITR (point-in-time recovery)
- Automated restore testing

**Cloud-Native Alternative:**
- Managed Postgres (RDS, Neon, Supabase) with automated backups
- Trades cost for operational simplicity

**Effort:** 3-4 hours for simple backup script + cron

**Priority:** P2 - Phase 5

---

### 🟠 11. CI/CD Pipeline Incomplete (DEPLOYMENT GAP)

**Current:** CI runs checks but no deployment.

**Plan:** "Movement between environments triggered by merge to main."

**Gaps:**
- No CD pipeline defined (push to registry? SSH deploy? K8s?)
- No environment promotion strategy (dev → staging → prod)
- No rollback procedure automated
- No blue-green or canary deployment strategy

**Decisions Needed:**
1. **Deployment Target:** Single VPS? Docker Swarm? K8s? Cloud Run?
2. **Image Registry:** Docker Hub? GHCR? Self-hosted?
3. **Deployment Method:** SSH + `docker compose pull`? Watchtower? ArgoCD?
4. **Zero-Downtime:** Required? (Implies rolling updates or blue-green)

**Recommendation (Personal Project Scale):**

**Simple:**
```bash
# GitHub Actions workflow
- Build images → Push to GHCR
- SSH to VPS
- docker compose pull
- docker compose up -d (rolling restart)
```

**Moderate:**
- GitHub Actions → GHCR
- Watchtower auto-update (polls registry, pulls new images)

**Advanced (Overkill):**
- ArgoCD or FluxCD (GitOps)
- K8s (unnecessary complexity for your scale)

**Effort:** 2-3 hours for simple SSH deploy

**Priority:** P2 - Post-Phase 5 (manual deployment fine for MVP)

---

### 🔵 12. Horizontal Scaling Not Addressed (FUTURE CONCERN)

**Current:** Single backend instance, single frontend instance.

**Implications:**
- Stateful sessions in DB allow scaling (good design choice)
- No load balancer defined yet (Traefik can do this)
- Database connection pooling configured but not tuned

**When Does This Matter?**
- Not for MVP or first few hundred users
- Becomes relevant if you open-source and see traffic spikes

**Assessment:** Your session design already supports horizontal scaling. Defer until needed.

**Priority:** P3 - Post-MVP (likely never needed for personal project)

---

## Technology Stack Assessment

### Python 3.12 + FastAPI: ⭐⭐⭐⭐⭐ (9/10)

**Strengths:**
- FastAPI is ideal for async Python APIs
- Modern type hints + Pydantic validation
- Auto-generated OpenAPI docs
- Async SQLAlchemy 2.0 (latest, best performance)
- Excellent ecosystem for auth (webauthn, passlib)

**Considerations:**
- Ensure all endpoints are async (don't block event loop)
- `psycopg[binary]` is good; `asyncpg` slightly faster but psycopg3 is excellent

**Verdict:** Perfect choice. No changes needed.

---

### React 19 + Vite: ⭐⭐⭐⭐ (7/10)

**Strengths:**
- React 19 has latest features (Server Components, new hooks)
- Vite is fast, modern build tool
- Good dev tooling (ESLint, Prettier)

**Concerns:**
- **React 19 is very new (stable Jan 2025)** - may hit bugs or library incompatibility
- No routing or state management chosen yet (decision paralysis risk)
- TypeScript types installed but not enforced (`.jsx` not `.tsx`)

**Recommendation:**
- **Option A:** Stay on React 19, accept bleeding-edge risk
- **Option B:** Downgrade to React 18 for stability (most libraries well-tested)
- **Type Safety:** Consider converting to TypeScript now (rename to `.tsx`, enable strict mode)

**Verdict:** Good choice, but React 18 would be safer for solo dev. Vite is perfect.

---

### PostgreSQL 16: ⭐⭐⭐⭐⭐ (10/10)

**Perfect choice for:**
- JSONB support (login_events.extra field)
- INET type (IP address logging with validation)
- Robust ACID guarantees
- Excellent Alembic/SQLAlchemy integration
- Native UUID support

**No alternatives needed.**

**Verdict:** Ideal for your use case. No changes needed.

---

### Docker Compose: ⭐⭐⭐⭐ (7/10)

**Good for:**
- Local development (excellent)
- Single-host production (adequate)

**Limitations:**
- No built-in service discovery beyond DNS
- No automatic failover
- Limited load balancing (can use Traefik for basic round-robin)

**When to Consider Alternatives:**
- Multi-host: Docker Swarm (simple) or K8s (complex)
- High availability: K8s with autoscaling

**Verdict:** Right choice for your scale. Don't over-engineer.

---

### Traefik (Planned): ⭐⭐⭐⭐ (8/10)

**Strengths:**
- Excellent for single-host reverse proxy
- Automatic TLS with Let's Encrypt
- Dynamic config via Docker labels
- Built-in dashboard
- Middleware support (compression, rate limiting, security headers)

**Considerations:**
- Learning curve for labels + middleware
- SSL cert storage needs backup (acme.json)
- Ensure you understand Let's Encrypt rate limits (50 certs/week/domain)

**Alternatives to Consider:**
- **Caddy:** Simpler config, automatic HTTPS, but less Docker integration
- **Nginx:** More manual but you already use it for frontend

**Verdict:** Traefik is a good choice. Stick with it.

---

### Redis (Planned): ⭐⭐⭐⭐⭐ (9/10)

**Essential for:**
- Challenge storage (security fix)
- Rate limiting
- Session caching (optional perf boost)

**Recommendation:**
- Image: `redis:7-alpine`
- Enable persistence: RDB for rate limit data
- Set `maxmemory-policy allkeys-lru` for cache use
- Disable persistence for challenge storage (ephemeral data)

**Verdict:** Must-add in Phase 2 completion. Perfect fit.

---

### Vault (Planned): ⭐⭐ (5/10 for Your Use Case)

**Strengths:**
- Industry-standard secrets management
- Automated rotation
- Audit logging
- Dynamic secrets

**Concerns:**
- **High operational overhead** for single-person project
- Adds another service to monitor/backup
- Unseal process is manual (annoying for restarts)
- Learning curve is steep

**Recommendation:**
- **Phase 3:** Start with Docker Secrets (simpler, good enough)
- **Reconsider Vault** only if you hit these triggers:
  - Multiple services needing dynamic secrets
  - Automated secret rotation required
  - Compliance requirements

**Alternatives:**
- **Docker Secrets:** Built-in, simple, good for your scale
- **Doppler/Infisical:** SaaS, less operational burden
- **SOPS:** Encrypted files in Git, no runtime service

**Verdict:** Docker Secrets recommended. Vault is overkill.

---

## Architectural Decisions to Make

### High Priority (Before Phase 3)

#### 1. Redis Integration Approach
**Decision:** Add Redis to compose files now or wait until Phase 3?

**Recommendation:** Add now (Phase 2 completion) to fix challenge storage vulnerability.

**Action Items:**
- Add `redis:7-alpine` to `compose.dev.yml`
- Add `redis` Python client to `requirements.txt`
- Refactor WebAuthn endpoints to use Redis for challenge storage

---

#### 2. Traefik Configuration Strategy
**Decision:** Static config file or dynamic via Docker labels?

**Recommendation:** Dynamic via Docker labels (easier per-service maintenance).

**Action Items:**
- Create `traefik/traefik.yml` for static config (entry points, TLS certresolver)
- Add Docker labels to `compose.prod.yml` for routing rules
- Test with Let's Encrypt staging endpoint first

---

#### 3. CSRF Protection Pattern
**Decision:** Double-submit cookie (stateless) or synchronizer token (stateful)?

**Recommendation:** Double-submit cookie (simpler, sufficient for your threat model).

**How it works:**
1. Server sets CSRF token in cookie (HttpOnly=false, so JS can read)
2. Client reads cookie, sends value in custom header (X-CSRF-Token)
3. Server validates cookie matches header

**Action Items:**
- Add CSRF middleware to FastAPI
- Update frontend to send X-CSRF-Token header

---

#### 4. Secrets Management Strategy
**Decision:** Docker Secrets vs. Vault vs. Other?

**Recommendation:** Docker Secrets for Phase 3, reconsider Vault later if needed.

**Action Items:**
- Create secrets files (db_password, jwt_secret, smtp_password)
- Update `compose.prod.yml` to use secrets
- Modify backend code to read from `/run/secrets/`

---

### Medium Priority (Phase 4-5)

#### 5. Testing Database Strategy
**Decision:** Separate test DB instance? In-memory SQLite? Same DB with prefix?

**Recommendation:** Separate PostgreSQL test DB (mirrors production).

**Action Items:**
- Create pytest fixture to spin up/tear down test DB
- Use SQLAlchemy's `create_all()` for schema creation
- Ensure tests clean up after themselves

---

#### 6. Backup Storage Location
**Decision:** Local-only or off-host? Cloud storage provider?

**Recommendation:** Local volume + rsync to off-host (Backblaze B2 or rsync.net).

**Action Items:**
- Write `pg_dump` backup script
- Set up cron job (daily at 2 AM)
- Configure rsync to B2 or rsync.net
- Document restore procedure

---

#### 7. Observability Collectors
**Decision:** Self-hosted (Grafana stack) or SaaS (Honeycomb, Datadog)?

**Recommendation:** Start with Honeycomb free tier (easier), move to self-hosted later if needed.

**Action Items:**
- Sign up for Honeycomb (or similar)
- Update OTEL_OTLP_ENDPOINT to point to collector
- Create basic dashboards for request latency, error rates

---

### Low Priority (Post-MVP)

#### 8. Feature Flags System
**Decision:** Simple env vars or dedicated system (Unleash, LaunchDarkly)?

**Recommendation:** Defer until needed. Use env vars if/when required.

---

#### 9. Multi-Tenancy Support
**Decision:** Will you ever support "teams" or shared workout plans?

**Recommendation:** Defer. Current schema is single-user. Add `tenant_id` later if needed.

---

## Recommended Additions

### 1. Add API Versioning ⭐⭐⭐⭐⭐

**Why:** Breaking changes become painful without versioning.

**How:** Prefix routes with `/api/v1/` instead of `/api/`.

**Changes:**
```python
# main.py
app.include_router(auth_router, prefix="/v1")
```

**Frontend proxy config:**
```js
// vite.config.js
proxy: {
  '/api/v1': {
    target: 'http://backend:8000',
    rewrite: (path) => path.replace(/^\/api\/v1/, '/v1')
  }
}
```

**Effort:** 1 hour (refactor router includes + frontend proxy)

**Priority:** P1 - Add before Phase 3

---

### 2. Enhance OpenAPI Documentation ⭐⭐⭐⭐

**Why:** You specified "self-documenting APIs meeting OpenAPI standards."

**Current Gap:** FastAPI auto-generates docs, but missing `response_model` and detailed descriptions.

**Example Enhancement:**
```python
@router.post("/magic-link/start", response_model=MagicLinkStartResponse)
async def request_magic_link(
    request: MagicLinkStartRequest,
    db: AsyncSession = Depends(get_db)
) -> MagicLinkStartResponse:
    """
    Request a magic link authentication email.

    Sends a single-use, time-limited magic link to the provided email address.
    Returns a generic success message to prevent email enumeration.

    Rate limit: 5 requests per minute per IP.
    """
    ...
```

**Effort:** 2-3 hours to enhance existing endpoints

**Priority:** P2 - Phase 4

---

### 3. Add Health Check Detail Levels ⭐⭐⭐

**Why:** Kubernetes-style health checks for better orchestration.

**Current:** `/healthz` returns `{"status": "ok"}`.

**Better:**
- `/healthz/live` - Basic liveness (process running?)
- `/healthz/ready` - Deep readiness check (DB connected? Redis reachable?)

**Example:**
```python
@router.get("/healthz/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Deep health check (DB, Redis, etc.)"""
    try:
        # Check DB
        await db.execute(text("SELECT 1"))
        # Check Redis
        await redis.ping()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Not ready")
```

**Effort:** 30 minutes

**Priority:** P2 - Phase 4

---

### 4. Return Correlation IDs in Responses ⭐⭐⭐

**Why:** Client-side debugging and support.

**Current:** Request IDs tracked internally only.

**Better:** Return `X-Request-ID` header in responses.

**Changes:**
```python
# middleware/request_id.py
response.headers["X-Request-ID"] = request_id
```

**Effort:** 15 minutes

**Priority:** P2 - Phase 4

---

### 5. Add Structured Error Responses ⭐⭐⭐⭐

**Why:** Consistent error handling for frontend.

**Current:** FastAPI defaults (some are HTML).

**Better:** Consistent JSON format.

**Example:**
```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "The provided token is invalid or expired",
    "request_id": "abc123"
  }
}
```

**Implementation:**
```python
# main.py
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = request.state.request_id
    log.error("unhandled_exception", request_id=request_id, exc_info=exc)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id
            }
        }
    )
```

**Effort:** 1-2 hours (custom exception handler + error models)

**Priority:** P2 - Phase 4

---

### 6. Tune Database Connection Pooling ⭐⭐⭐

**Why:** Default settings may not be optimal for your workload.

**Current:** SQLAlchemy defaults (likely 5-10 connections).

**Recommendation:**
```python
# db/database.py
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,          # Persistent connections
    max_overflow=20,       # Additional connections under load
    pool_pre_ping=True,    # Validate connections before use
    pool_recycle=3600      # Recycle connections every hour
)
```

**Effort:** 10 minutes

**Priority:** P2 - Phase 3

---

## Phase-by-Phase Action Plan

### Phase 2 (Current) - Security Hardening & Minimal UI

**Status:** In progress - Backend auth complete, frontend UI missing

**Critical Security Fixes (BLOCKING):**

1. **Add Redis to Dev Stack** (30 min)
   ```yaml
   # compose.dev.yml
   redis:
     image: redis:7-alpine
     ports:
       - "6379:6379"
     command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
   ```

2. **Fix WebAuthn Challenge Storage** (2-3 hours)
   - Add `redis` Python client to requirements.txt
   - Create challenge storage module (`app/core/challenge_storage.py`)
   - Update `/register/start` and `/authenticate/start` to store challenges in Redis
   - Update `/register/finish` and `/authenticate/finish` to retrieve + validate + delete
   - TTL: 30 seconds

3. **Add CSRF Protection** (1-2 hours)
   - Implement double-submit cookie pattern
   - Add CSRF middleware
   - Update frontend to send X-CSRF-Token header

4. **Activate Session Rotation** (1 hour)
   - Add rotation trigger after WebAuthn credential addition
   - Add time-based rotation check (every 7 days)

**Frontend UI (for MVP):**

5. **Choose Routing Library** (30 min decision)
   - Recommendation: React Router v6
   - Alternative: TanStack Router (if you want type-safe routes)

6. **Build Minimal Auth Screens** (8-12 hours)
   - Magic link request page (email input form)
   - Magic link verify page (parse token from URL, call `/verify`)
   - WebAuthn registration flow (after magic link login)
   - WebAuthn login flow (for returning users)
   - Protected route wrapper (redirect to login if no session)
   - Basic navigation/layout

**Definition of Done:**
- [ ] Redis integrated and challenge storage fixed
- [ ] CSRF protection implemented
- [ ] Session rotation active
- [ ] User can sign in via magic link (full E2E flow)
- [ ] User can register and use passkey (full E2E flow)
- [ ] User can log out
- [ ] Manual testing of all auth flows documented

**Estimated Effort:** 16-20 hours

---

### Phase 3 - Production Serving, Traefik, TLS, Secrets

**Prerequisites:** Phase 2 complete (auth MVP working)

**Activities:**

1. **Set Up Traefik** (4-6 hours)
   - Create `traefik/traefik.yml` (static config)
   - Create `compose.traefik.yml` (Traefik service)
   - Add Docker labels to `compose.prod.yml` for routing
   - Configure Let's Encrypt certresolver (staging first!)
   - Test locally with mkcert for TLS

2. **Implement Rate Limiting** (2-3 hours)
   - Add slowapi to requirements
   - Configure Redis backend for rate limit storage
   - Apply to auth endpoints (5/min for magic link, 10/min for WebAuthn start)

3. **Switch to Docker Secrets** (2-3 hours)
   - Create secrets files
   - Update `compose.prod.yml` to use secrets
   - Modify backend to read from `/run/secrets/`
   - Test secret rotation procedure

4. **Tune Gunicorn** (1 hour)
   - Configure workers: `(2 * CPU_CORES) + 1`
   - Set `worker_class = "uvicorn.workers.UvicornWorker"`
   - Add graceful shutdown handling
   - Test under load (use `wrk` or `locust`)

5. **Add API Versioning** (1 hour)
   - Prefix routes with `/v1`
   - Update frontend proxy config
   - Update RUNBOOK.md

**Definition of Done:**
- [ ] `make prod-up` serves HTTPS on `rutabagel.com`
- [ ] No CORS errors in prod
- [ ] Secrets loaded from Docker secrets
- [ ] Health checks visible in Traefik dashboard
- [ ] Rate limiting prevents brute force (verified with test script)
- [ ] TLS certificate auto-renews (test with staging, verify with prod)

**Estimated Effort:** 12-16 hours

---

### Phase 4 - Testing & CI

**Prerequisites:** Phase 3 complete (prod deployment working)

**Activities:**

1. **Set Up Pytest Structure** (4-6 hours)
   ```
   backend/tests/
   ├── conftest.py          # Fixtures (test DB, test client)
   ├── test_auth.py         # Auth endpoints
   ├── test_models.py       # SQLAlchemy models
   ├── test_security.py     # Token hashing, validation
   └── test_session.py      # Session management
   ```

2. **Create Test Database Fixture** (2 hours)
   - Spin up/tear down test DB per session
   - Use SQLAlchemy's `create_all()` for schema
   - Clean up test data after each test

3. **Write Core Tests** (8-12 hours)
   - Magic link flow (start, verify, invalid token)
   - WebAuthn registration (happy path, replay attack)
   - WebAuthn authentication (happy path, wrong credential)
   - Session validation (expired, revoked, rotated)
   - CSRF protection (with/without token)
   - Rate limiting (exceed limit, verify backoff)

4. **Add Frontend Tests** (4-6 hours)
   - Set up Vitest
   - Test auth context (login, logout state changes)
   - Test form validation
   - Test protected route redirects

5. **Enhance CI Pipeline** (2-3 hours)
   - Remove `|| true` from pytest command
   - Add coverage reporting (pytest-cov)
   - Add frontend tests to CI
   - Add migration check (ensure clean after upgrade)
   - Add prod image build to CI (fail if build fails)

6. **Enhance OpenAPI Docs** (2-3 hours)
   - Add `response_model` to all endpoints
   - Add detailed descriptions
   - Add example requests/responses

**Definition of Done:**
- [ ] CI fails on test failures
- [ ] Backend test coverage >70% (aim for 95% eventually)
- [ ] Frontend test coverage >60%
- [ ] Lint, type check, security audit jobs run
- [ ] Prod images build in CI
- [ ] Migration check passes

**Estimated Effort:** 24-32 hours

---

### Phase 5 - Preview/Staging, Backups, Runbooks

**Prerequisites:** Phase 4 complete (tests passing)

**Activities:**

1. **Set Up Staging Environment (Optional)** (3-4 hours)
   - Duplicate prod setup with staging subdomain
   - Configure Traefik routing for staging
   - Use separate database
   - Test deployment process

2. **Implement Backup Automation** (3-4 hours)
   - Write backup script (`scripts/backup_db.sh`)
   - Set up cron job (daily at 2 AM)
   - Configure rsync to off-host storage (Backblaze B2)
   - Implement retention policy (7 daily + 4 weekly + 3 monthly)

3. **Create Restore Procedure** (2-3 hours)
   - Write restore script (`scripts/restore_db.sh`)
   - Document manual restore steps
   - Test restore on staging environment
   - Schedule monthly restore tests

4. **Expand RUNBOOK.md** (3-4 hours)
   - Bring-up procedure (from cold start)
   - Update procedure (pull new images, apply migrations)
   - Rollback procedure (revert to previous image)
   - Backup/restore procedures
   - Secret rotation procedures
   - Incident response playbook

5. **Add Observability Collectors** (4-6 hours)
   - Sign up for Honeycomb (or self-host Grafana stack)
   - Update OTEL_OTLP_ENDPOINT
   - Create basic dashboards (request latency, error rates, auth success/failure)
   - Set up alerts (error rate spike, health check failure)

**Definition of Done:**
- [ ] (Optional) Staging environment reachable
- [ ] Nightly DB backups exist
- [ ] Backups uploaded to off-host storage
- [ ] Restore procedure documented and tested
- [ ] RUNBOOK.md covers all common ops tasks
- [ ] Observability dashboards visible
- [ ] Alerts configured for critical failures

**Estimated Effort:** 16-24 hours

---

### Post-Phase 5 - Feature Development

**At this point, infrastructure is production-ready. Begin building workout tracking features:**

1. **Program Management**
   - Define exercises (name, muscle group, equipment)
   - Create programs (collection of exercises)
   - Define workout templates (sets, reps, rest periods)

2. **Workout Logging**
   - Start workout from program
   - Log sets (reps, weight, perceived exertion)
   - Notes and timestamps
   - Complete/abandon workout

3. **Analytics & Insights**
   - Progress charts (weight over time, volume over time)
   - Personal records (PRs)
   - Correlation analysis (sleep vs. performance, etc.)
   - Trend detection

**Each feature should follow:**
- Write tests first (TDD)
- Create migration for schema changes
- Build API endpoints
- Build frontend UI
- Update documentation

---

## Detailed Ratings by Category

| Category | Score | Notes |
|----------|-------|-------|
| **Security** | 8/10 | Strong foundation, critical gaps (challenge storage, CSRF) need immediate fix |
| **Scalability** | 7/10 | Good session design supports horizontal scaling, but single-instance limits |
| **Observability** | 7/10 | Infrastructure correctly implemented, collectors/dashboards missing |
| **Developer Experience** | 9/10 | Excellent local dev setup, Makefile, pre-commit hooks |
| **Production Readiness** | 5/10 | Good foundation, but Traefik + TLS + secrets + backups needed |
| **Code Quality** | 8/10 | Strong hooks and tooling, but no tests yet (target: 95% coverage) |
| **Documentation** | 7/10 | Good operational docs (RUNBOOK.md), API docs need enhancement |
| **Database Design** | 10/10 | Well-normalized, proper indexes, robust schema |
| **API Design** | 7/10 | RESTful, but needs versioning + enhanced OpenAPI docs |
| **Testing** | 3/10 | Infrastructure in place (pytest, httpx) but no tests written |

**Overall: 7.5/10** - Strong foundation with clear path to production

---

## Open Questions

### High Priority (Need Answers Before Phase 3)

1. **Deployment Target**
   - What's your production environment? (VPS? Cloud provider? Self-hosted?)
   - Which VPS provider? (DigitalOcean, Linode, Hetzner, AWS Lightsail?)
   - Server specs? (vCPUs, RAM, storage?)

2. **Domain & DNS**
   - Do you own `rutabagel.com`?
   - Is DNS configured to point to your server?
   - Subdomain strategy? (`app.rutabagel.com` vs. root domain?)

3. **Backup Storage**
   - Budget for off-host backup storage?
   - Preference: Backblaze B2 ($5/TB/month)? rsync.net? AWS S3?

### Medium Priority (Decide During Phase 4-5)

4. **Observability SaaS**
   - Self-hosted Grafana stack or SaaS (Honeycomb, Datadog)?
   - Budget considerations?

5. **Error Tracking**
   - Want error tracking service? (Sentry free tier, GlitchTip self-hosted?)

6. **Uptime Monitoring**
   - Want external uptime monitoring? (UptimeRobot free tier, Healthchecks.io?)

### Low Priority (Post-MVP)

7. **Open Source Plans**
   - Will you open-source FitFolio?
   - If yes, need to consider:
     - License choice (MIT, GPL, AGPL?)
     - Community contribution guidelines
     - Issue templates, PR templates
     - Public demo instance?

8. **Mobile App**
   - Future consideration: PWA? React Native? Flutter?

---

## Next Steps

### Immediate (This Week)
1. ✅ Add Redis to `compose.dev.yml`
2. ✅ Fix WebAuthn challenge storage vulnerability
3. ✅ Add CSRF protection
4. ✅ Activate session rotation

### Soon (Next 1-2 Weeks)
5. Decide on frontend routing library (React Router v6 recommended)
6. Build minimal auth UI (magic link + WebAuthn flows)
7. Manual E2E testing of all auth flows

### Later (Phase 3+)
8. Create Traefik configuration
9. Implement rate limiting
10. Switch to Docker Secrets
11. Begin test writing (Phase 4)

---

## Conclusion

**FitFolio has a solid architectural foundation** with modern best practices baked in from the start. The authentication design is enterprise-grade, the database schema is well-thought-out, and the development experience is excellent.

**The main gaps are operational:** Traefik configuration, secrets management, backups, and comprehensive testing. These are well-understood problems with clear solutions outlined in this document.

**Recommendation:** Focus on completing Phase 2 (fix security vulnerabilities + build minimal UI), then move confidently into Phase 3 (production deployment). Don't over-engineer—Docker Secrets are sufficient, Vault is overkill, and your current scale doesn't require Kubernetes or complex service mesh.

**You're on the right track.** Execute the phase-by-phase plan, and FitFolio will be production-ready and maintainable.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-27
**Next Review:** After Phase 2 completion
