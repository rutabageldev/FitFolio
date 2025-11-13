### ADR 0001: Adopt API contract tests

Context

- Prevent accidental breaking changes to public API versioning and paths.

Decision

- Maintain `backend/tests/contract/` with minimal assertions (existence, versioned
  paths, basic status).
- Run on every PR via pre-commit and CI.

Consequences

- Earlier detection of regressions; faster, safer releases.
