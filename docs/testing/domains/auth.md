### Domain: Auth

Sub-areas

- Email verification: `backend/tests/auth/email/`
- Magic link: `backend/tests/auth/magic_link/`
- Sessions: `backend/tests/auth/sessions/`
- WebAuthn/passkeys: `backend/tests/auth/webauthn/`

Invariants

- All public routes are under `/api/v1/auth/...`
- CSRF required for state-changing requests.
- Session cookies: HttpOnly, SameSite=Lax, Secure when configured.

No-mock paths

- Maintain at least one end-to-end path for magic link and WebAuthn
  registration/authentication.
