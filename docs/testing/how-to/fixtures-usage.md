### Fixtures usage

Core fixtures (see `backend/tests/conftest.py`)

- `client` (httpx `AsyncClient` bound to FastAPI app)
- `db_session` (transactional session, rolled back per test)
- `csrf_token` (valid token pair for CSRF-protected routes)
- `test_user` (persisted user model)

Guidelines

- Prefer function-scoped fixtures for isolation.
- Encapsulate time/randomness in fixture parameters.
- Compose fixtures; avoid global state.
- Document domain-specific fixtures in `domains/*`.

Discover fixtures

- List all:
  `docker compose -f compose.dev.yml exec -T backend bash -lc 'pytest --fixtures -q'`
- Capture to docs: see `docs/testing/reference/fixtures.md`.
