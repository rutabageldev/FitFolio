### Pytest markers

Defined in `backend/pytest.ini`

- unit: Unit tests (fast, no external dependencies)
- integration: Integration tests (may use database, HTTP client)
- security: Security-related tests (CSRF, sessions, rotation)
- contract: API contract tests (verify endpoints exist at expected paths)
- admin: Admin-related tests (audit logs, privileged endpoints)
- slow: Tests that take a long time to run
