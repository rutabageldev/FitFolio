### Testing documentation index

Audience-optimized entry point. Keep this page short and link out.

- For QA
  - Strategy: see `docs/testing/strategy.md`
  - Playbooks: `docs/testing/playbooks/`
  - Reference (fixtures, markers, buckets): `docs/testing/reference/`
- For backend developers
  - How-to: `docs/testing/how-to/` (add tests, mocking policy, fixtures, naming,
    contract/security tests, CI)
  - Domains: `docs/testing/domains/` (auth, security, deps, admin, contract)
- For reviewers
  - Review checklist: `docs/testing/templates/review_checklist.md`
  - Governance and DoD: `docs/testing/governance.md`
  - Coverage targets: `docs/testing/coverage.md`

Conventions

- Prefer minimal mocking; mock only true external I/O.
- Tests must be deterministic, isolated, and order-independent.
- Each critical flow has a no-mock path.
- Use explicit markers from `pytest.ini` (`unit`, `integration`, `security`, `contract`,
  `admin`, `slow`).
