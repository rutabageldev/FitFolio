### Test strategy (industry best practices)

Goals

- High-confidence commits with automatic deploys backed by exceptional QA.
- Fast feedback locally and in CI; stable, deterministic test outcomes.

Principles

- Test pyramid: many unit tests, fewer integration tests, few end-to-end.
- Minimal mocking: only mock true external I/O (SMTP, external HTTP, browser APIs).
- Determinism: isolate time, randomness, and environment; forbid network in unit tests.
- Colocation and clarity: colocate domain tests (auth/security/etc.) and use descriptive
  names.
- Contract-first boundaries: verify public APIs via contract tests and keep docs in
  sync.
- Security-by-default: protect auth/session/CSRF paths with dedicated tests and markers.
- Performance: keep test runtime budgeted; catch regressions early.

Markers (from pytest.ini)

- unit: fast, no external dependencies.
- integration: app-level with DB and Redis.
- security: CSRF, sessions, rotation, rate limiting.
- contract: endpoint existence and versioning.
- admin, slow: privileged flows; long-running.

Mocking policy

- Allowed: SMTP/email delivery, third-party HTTP APIs, browser credential responses.
- Not allowed in integration tests: DB session, Redis client, request pipeline.
- Maintain at least one “no-mock” path per critical flow.

Quality gates (CI)

- Lint/type/security: ruff, ruff-format, mypy, bandit.
- Contract tests must pass on every PR; endpoints cannot regress.
- Coverage thresholds: overall ≥ 85%; security-critical modules target ≥ 90%.
- Flake policy: zero-tolerance; fix root cause, do not add retries.

Data and state

- Use factory helpers and explicit fixtures for time and IDs.
- Reset DB/Redis state per test function (function-scoped fixtures).
- Avoid inter-test coupling; order independence is required.

Ownership and reviews

- Every test change follows the review checklist.
- Definition of Done includes updated docs and test plans when public behavior changes.
