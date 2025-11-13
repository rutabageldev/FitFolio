### Mocking policy (minimal, external-only)

Rationale

- Over-mocking hides integration defects; we aim for high confidence and stable deploys.

Allowed to mock

- SMTP/email delivery and third-party HTTP services.
- Browser/WebAuthn client responses (structured objects only), while keeping at least
  one no-mock path.

Not allowed to mock in integration tests

- Database session/engine, Redis client, request/ASGI stack, business logic.

Practices

- Prefer realistic payloads and schemas; verify shapes via contract tests.
- Keep mock scopes tight; use context managers or fixtures.
- Avoid patching deep internals; patch at module boundaries.

No-mock coverage

- Ensure one end-to-end path per critical flow (magic link, session rotation, WebAuthn).
