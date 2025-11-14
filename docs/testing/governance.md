### Testing governance

Ownership

- Domain owners maintain domain docs and fixtures.
- PRs touching public behavior must update relevant docs/playbooks.

Definition of Done (testing)

- Appropriate tests added/updated; pre-commit and CI pass.
- Coverage meets thresholds; artifacts published.
- Review checklist completed.

Flaky tests

- Zero tolerance. Quarantine behind a feature flag if needed, then fix.
- No CI retries used to mask flakiness.

Documentation lifecycle

- Keep pages ≤ 200 lines; split when larger.
- Each page lists owners and “Last verified” date.
