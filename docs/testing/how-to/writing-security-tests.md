### Writing security tests

Focus areas

- CSRF, session rotation, rate limiting, account lockout, auth flows (magic link,
  WebAuthn).

Practices

- Mark with `@pytest.mark.security` (+ `@pytest.mark.integration`).
- Cover happy paths, error paths, and abuse cases.
- Assert on headers, cookies, CSRF tokens, SameSite/Secure/HttpOnly flags.
- Maintain at least one end-to-end path without mocks for each critical flow.

Operational

- Add regression tests for any security bug fixed.
- Keep payloads realistic; avoid over-stubbing cryptographic primitives.
