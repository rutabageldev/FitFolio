### Coverage policy

Targets

- Overall backend ≥ 85%; security-critical modules target ≥ 90%.

Reporting

- Local: `pytest --cov=app --cov-report=term-missing --cov-report=html`
- CI: publish HTML and XML artifacts; fail if thresholds unmet.

Granularity

- Track by module and by domain bucket; prioritize hot paths.

Quality

- Avoid “gaming” coverage; prefer meaningful assertions and branch coverage.
