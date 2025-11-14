# ADR-0006: Adopt API Contract Tests

**Status:** Accepted **Date:** 2025-11-13 **Deciders:** Core team **Tags:** testing,
api, backend, ci

## Context

Public API paths and versioning are critical external contracts. Recent refactors
increased test coverage and reorganized suites, but we lacked a lightweight, always-on
guardrail to prevent accidental breaking changes to endpoint existence and versioned
paths. We need a small, stable test layer that fails fast when routes move or disappear,
without overfitting business logic.

Constraints and requirements:

- Keep assertions minimal (existence, versioned paths, basic unauthenticated statuses).
- Execute quickly on every PR and in pre-commit.
- Complement, not replace, domain tests and integration tests.

## Decision

Adopt API contract tests maintained under `backend/tests/contract/`:

- Verify endpoint existence and versioned paths (`/api/v1/...`), using parametric
  inventories.
- Assert “not 404” (or expected unauthenticated defaults) rather than detailed business
  behavior.
- Mark tests with `@pytest.mark.contract` and `@pytest.mark.integration`.
- Run in pre-commit and CI on every PR.

## Rationale

Key factors:

- Moves/renames to public routes are common regression sources.
- Minimal assertions yield stability, speed, and low maintenance.
- Clear separation from domain tests keeps business behavior elsewhere.

Alternatives considered:

- Rely solely on domain/integration tests: higher maintenance and slower feedback for
  simple path regressions.
- API schema diff-only checks: useful but insufficient to catch runtime routing errors
  and environment-specific paths.

## Consequences

### Positive

- Fast, deterministic detection of breaking API path/version changes.
- Clear ownership of public surface guarantees with low maintenance.

### Negative

- Additional suite to maintain (small).
- Potential false sense of coverage if misused for business assertions (mitigated by
  scoping).

### Neutral

- Encourages explicit documentation and inventories of public endpoints.

## Implementation

- Directory: `backend/tests/contract/`
- Patterns:
  - Parametric inventories for methods/paths.
  - Accept non-404 for existence checks; log when statuses differ from unauthenticated
    defaults.
- Tooling:
  - Pre-commit hook runs contract tests (see `.pre-commit-config.yaml`).
  - CI executes full test matrix; contract tests are required to pass.
- Related changes:
  - `docs/testing/how-to/writing-contract-tests.md` documents authoring guidance.

## References

- `backend/tests/contract/` in this repo
- Testing strategy: `docs/testing/strategy.md`
- Authoring contract tests: `docs/testing/how-to/writing-contract-tests.md`
