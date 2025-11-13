## QA Get‑Well Plan

Note: The canonical testing documentation now lives under `docs/testing/`. Start at
`docs/testing/README.md`.

### Scope and Objectives

- Strengthen automated testing to ensure high confidence in security‑critical auth flows
  and accelerate feature delivery for the FitFolio MVP.
- Reduce duplication in tests, enforce consistent standards, and formalize documentation
  and CI expectations.

### Product and Architecture Snapshot

- Purpose: Personal fitness tracking web app with passwordless authentication (magic
  link + WebAuthn/passkeys) and strong security.
- Status: Backend auth/security foundation complete (Phase 2B). Frontend scaffold in
  place. Production deployment next.
- Stack: FastAPI (Python 3.12), SQLAlchemy/Alembic, Postgres, Redis, structlog,
  OpenTelemetry; React 19 + Vite.
- API: Versioned under `/api/v1`; health at `/healthz`.

### Current Test Automation Overview

- Backend
  - Pytest with async support, rich fixtures (in‑memory SQLite engine with Postgres type
    adapters, httpx `AsyncClient`, real Redis by default), coverage reports (HTML/XML).
  - Suites cover: magic link flows, WebAuthn, CSRF, session rotation, rate limiting,
    account lockout, audit logging, and API contract checks.
  - Test plans exist under `backend/tests/test_plans/*` with an index tracking coverage
    gaps and targets.
- Frontend
  - Vitest configured with jsdom and coverage reporters; initial app scaffold; no test
    files yet.
- CI
  - CI exists and runs successfully at `.github/workflows/ci.yml`. Use it to enforce
    gates and publish artifacts.

## Baseline Test Standards and Goals

### Test Levels

- Unit tests
  - Purpose: Fast, isolated validation of functions/modules.
  - Environment: In‑memory SQLite; no network; patch only true I/O boundaries.
  - Targets: ≥85% per backend module; ≥80% per frontend package initially.
  - Mark with `@pytest.mark.unit`.
- Integration tests
  - Purpose: Exercise realistic behavior through the FastAPI app boundary with minimal
    mocking.
  - Environment: httpx `AsyncClient` against the ASGI app; real Redis. For “full” paths,
    run against Postgres via Compose.
  - Targets: ≥80% per integration area; ≥90% for security‑critical flows (auth, CSRF,
    sessions, rate limiting, WebAuthn).
  - Mark with `@pytest.mark.integration`; tag sensitive paths with
    `@pytest.mark.security`.

### Mocking Policy

- Minimize mocking. Only mock true external I/O:
  - SMTP/email, third‑party HTTP APIs, browser credential responses that cannot be
    produced server‑side.
- Do not mock internal business logic, DB sessions, Redis client, or request pipeline in
  integration tests.
- Maintain at least one “no‑mock” path per critical flow to maximize utility and detect
  integration regressions early.

### Coverage and Quality Gates

- Overall coverage gate: ≥85% (enforced in CI).
- Security‑critical modules recommended: ≥90% (tracked and alerted in CI logs).
- Keep term‑missing reports to highlight gaps; publish XML/HTML as CI artifacts.
- Parallelize with `pytest-xdist` in CI for speed; ensure tests are order‑independent.

### Test Design and Organization

- Small, behavior‑focused tests; descriptive names; prefer parametrization for input
  matrices.
- Clear separation of unit vs integration via markers and directories.
- Shared, stable fixtures in `tests/conftest.py`; domain‑specific fixtures colocated per
  package if needed.

## Organization and Tracking

### Documentation

- Establish `docs/testing/` as the canonical home for:
  - `TEST_STRATEGY.md` (this plan distilled into policy), execution guidance, and CI
    notes.
  - Per‑module plans migrated or linked from `backend/tests/test_plans/*` (auth,
    webauthn, deps, rate_limit, etc.).
  - Coverage snapshots and deltas per release/PR (e.g., `docs/testing/coverage.md`).
- Link quickstart testing commands from `docs/RUNBOOK.md` to the above.

### Test Tree (Proposed Backend Layout)

- `backend/tests/auth/`
  - `test_magic_link_start.py`
  - `test_magic_link_verify.py`
  - `test_sessions.py`
  - `test_webauthn_register.py`
  - `test_webauthn_login.py`
- `backend/tests/security/`
  - `test_csrf.py`
  - `test_rate_limiting.py`
  - `test_session_rotation.py`
  - `test_request_id.py`
- `backend/tests/admin/`, `backend/tests/deps/`, etc., as needed.
- Keep common fixtures in `backend/tests/conftest.py`; add domain fixtures only when
  necessary.

### Frontend Test Layout

- Add `frontend/src/__tests__/` and colocated `*.test.tsx` files.
- Initial coverage:
  - App render smoke test.
  - API client utilities (headers/CSRF handling, error states).
  - First interactive component tests (email submit flow placeholder, passkey prompts).

## Redundancy and Consolidation Plan

### Observed Overlap

- Multiple files assert similar magic link start/verify behaviors:
  - `test_auth_endpoints.py` (large, mixed scope)
  - `test_auth_magic_link_happy_paths.py`
  - `test_auth_integration.py`
  - `test_auth_real_integration.py`
- WebAuthn registration/login coverage duplicated across general and “no‑mock” suites.

### Consolidation Actions

- Split `test_auth_endpoints.py` into focused files:
  - Start flows → `tests/auth/test_magic_link_start.py`
  - Verify flows → `tests/auth/test_magic_link_verify.py`
  - Session behaviors → `tests/auth/test_sessions.py`
- Merge overlapping integration suites:
  - Fold `test_auth_integration.py` and `test_auth_real_integration.py` into the
    behavior‑focused files, retaining one minimal/no‑mock variant where valuable.
  - Either keep `test_auth_webauthn_no_mocks.py` as a focused, “no‑mock” WebAuthn suite
    or merge its unique cases into `test_webauthn_*` and remove the standalone file.
- Ensure session rotation assertions live in `security/test_session_rotation.py` to
  avoid duplication.
- Apply markers consistently: `unit`, `integration`, `security`.

## CI Integration (Existing)

- CI exists and runs at `.github/workflows/ci.yml`.
- Recommendations:
  - Enforce `--cov-fail-under=85` for backend on CI.
  - Run `pytest -n auto` with xdist; upload HTML/XML coverage as artifacts.
  - Run Vitest with coverage; introduce soft thresholds initially (e.g., 60–70%),
    tightening to ≥80% as tests land.
  - Optionally publish coverage badges and summaries in PRs.

## Actionable Next Steps

- Backend
  - Consolidate auth tests into behavior‑focused files; remove duplicates.
  - Add missing error‑path tests identified in `backend/tests/test_plans/INDEX.md`
    (auth, webauthn, deps).
  - Turn on CI coverage gate (85%) and parallel execution.
- Frontend
  - Bootstrap Vitest smoke tests and API utility tests.
  - Add first component tests for auth‑related UI as it’s implemented.
- Documentation
  - Create `docs/testing/TEST_STRATEGY.md` from this plan; link test plans and CI
    details.
  - Keep coverage snapshots and track deltas per milestone.

### Definition of Done (Initial Get‑Well)

- CI enforces ≥85% backend coverage and runs tests in parallel.
- Redundant backend tests consolidated with clearly scoped behavior files.
- Frontend has baseline smoke and utility tests with coverage reporting.
- Testing strategy documented under `docs/testing/` and linked from the runbook.
