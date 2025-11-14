### Playbook: Magic link

Golden path

- Start: POST `/api/v1/auth/magic-link/start` with CSRF
- Verify: POST `/api/v1/auth/magic-link/verify` with token
- Expect session cookie set with correct attributes

Error paths

- Invalid/expired token -> 400
- Replay attack -> 400/401

No-mock

- One end-to-end test without mocking email sending (store token server-side)
