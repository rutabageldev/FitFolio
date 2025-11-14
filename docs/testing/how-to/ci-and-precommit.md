### CI and pre-commit

Pre-commit hooks (run locally and in CI)

- Hygiene: large files, merge conflicts, EOF, trailing whitespace, YAML/JSON.
- Python: ruff (+fix), ruff-format, mypy, bandit.
- Frontend: eslint, prettier.
- Backend security tests: selected pytest suite.

Gates

- All hooks must pass; no exceptions unless unavoidable and documented via ADR.
- Branch protection requires green CI and pre-commit.
- Coverage must meet thresholds; publish HTML/XML artifacts.

Commands

- Run all hooks: `pre-commit run -a`
- Run specific: `pre-commit run ruff -a`
