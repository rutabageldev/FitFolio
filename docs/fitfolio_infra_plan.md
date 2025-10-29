# FitFolio Infrastructure Implementation Guide

This document outlines the phases, activities, objectives, and definitions of done (DoD) for FitFolio's infrastructure setup, based on the final design decisions:

- **Routing:** Single host `rutabagel.com` with backend at `/api` (no cross-origin CORS in prod).
- **Sessions:** Opaque, rotating, server-side sessions stored in Postgres, delivered via HttpOnly, Secure, SameSite=Lax cookie.
- **Email Auth Flow:** Magic link (single-use, short TTL) as the primary sign-in method, with WebAuthn (passkeys) prompted after login.

---

## Phase 0 — Local loop verified (Complete)

**Activities**

- Start Dev Container and `docker-compose` (dev).
- Verify backend `/healthz`, Mailpit receipt, and frontend ↔ backend calls in dev.

**Objective**

- Confirm end‑to‑end dev loop works.

**Definition of Done**

- `make up` boots all services without errors. (Complete)
- Frontend calls a sample API successfully. (Complete)
- Mailpit shows a test message. (Complete)
- `RUNBOOK.md` documents local start/stop/logs. (Complete)

---

## Phase 1 — Data model + migrations foundation (Complete)

**Activities**

- Add SQLAlchemy models: `User`, `Session`, `WebAuthnCredential`, `LoginEvent`.
- Wire Alembic to project metadata; create and apply initial migration.
- Add Make targets: `migrate`, `autogen`.

**Objective**

- Reliable, versioned DB layer ready for auth and beyond.

**Definition of Done**

- `alembic upgrade head` creates all tables.
- `alembic revision --autogenerate` is clean.
- `RUNBOOK.md` documents migration commands.

---

## Phase 2 — Auth MVP (Magic link + Passkeys, Opaque Sessions)

**Activities**

- Implement email magic link start/finish endpoints with single-use tokens.
- Implement opaque server-side sessions with rotation.
- Implement WebAuthn register/login endpoints.
- Add CSRF protections.
- Build minimal frontend screens for email sign‑in and passkey registration/login.

**Objective**

- Passwordless baseline with strong UX and security; passkeys ready from day one.

**Definition of Done**

- Email sign‑in creates a valid session cookie.
- Passkey registration + login works.
- Session rotation works; logout invalidates session.
- Happy‑path E2E flows manually validated and documented.

---

## Phase 3 — Production serving, Traefik, TLS, secrets

**Activities**

- Switch backend prod to `gunicorn` with uvicorn workers.
- Integrate with Traefik: frontend `/`, backend `/api` (strip prefix), TLS via certresolver.
- Move sensitive values to Docker secrets.

**Objective**

- Serve FitFolio securely over HTTPS behind Traefik with clean `/api` routing.

**Definition of Done**

- `make prod-up` serves HTTPS on `rutabagel.com`.
- No CORS errors in prod.
- Secrets loaded from Docker secrets.
- Health checks visible in Traefik dashboard.

---

## Phase 4 — Testing & CI

**Activities**

- Backend: add `pytest`, `pytest-asyncio`, `httpx` tests.
- Frontend: add `vitest` tests.
- CI: run backend & frontend tests, check migrations, build prod images.

**Objective**

- Prevent regressions and enforce migration discipline before merge.

**Definition of Done**

- CI fails on test or migration issues.
- Lint, type check, security audit jobs run.
- Prod images build in CI.

---

## Phase 5 — Preview/staging, backups, runbooks

**Activities**

- (Optional) Preview deploys via Traefik.
- Nightly DB backups with restore test.
- Write `RUNBOOK.md` for bring-up, update, rollback, backup/restore, key rotation.

**Objective**

- Make shipping safe and recovery straightforward.

**Definition of Done**

- (Optional) Preview reachable.
- Nightly DB backups exist and can be restored.
- Runbook covers all common ops tasks.

---

## Master Checklist

- [ ] Phase 0: Local loop verified
- [ ] Phase 1: Models + initial migration
- [ ] Phase 2: Auth MVP (magic link + WebAuthn, opaque sessions)
- [ ] Phase 3: Prod serving + Traefik (/api on rutabagel.com) + TLS + secrets
- [ ] Phase 4: Tests + CI (pytest, vitest, migration check, prod build)
- [ ] Phase 5: Preview (opt), backups, RUNBOOK
