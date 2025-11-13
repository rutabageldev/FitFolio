### Test catalog schema (backend-first)

Purpose

- Keep a machine-readable inventory of canonical test behaviors per domain.
- Enable simple reporting on implemented vs planned cases.

Schema (YAML)

- `schema`: integer version (current: 1)
- `area`: domain key (auth, security, deps, admin, contract)
- `updated`: ISO date
- `owners`: list of owning teams/roles
- `items`: list of catalog entries
  - `id`: stable behavior ID (e.g., AUTH-ML-001)
  - `title`: behavior under test (concise)
  - `level`: unit | integration | e2e
  - `markers`: pytest markers (e.g., [security, contract])
  - `risk`: low | medium | high
  - `status`: planned | implemented | deprecated
  - `tests`: list of code locations (file or node id)
  - `last_verified`: ISO date when validated green in CI

Editing rules

- Keep titles behavior-focused, not implementation-specific.
- Prefer linking tests via file path; add node id when stable.
- When behavior changes, update `last_verified`.
- Avoid duplication; consolidate via parametrization when possible.

Layout

- Backend catalogs live under `docs/testing/catalog/backend/`.
- Frontend catalogs will live under `docs/testing/catalog/frontend/` when added.

Running the report

- Prerequisites: Python 3 and `pyyaml` (install once with
  `python3 -m pip install pyyaml`).
- Generate the report:

```bash
python3 scripts/build_catalog_report.py
```

- Output: `docs/testing/catalog/backend/report.json` with per-bucket implementation
  rates, totals, duplicate ID check, and unreferenced backend test files to backfill.
