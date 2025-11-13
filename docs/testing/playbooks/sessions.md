### Playbook: Sessions

Golden path

- `/api/v1/auth/me` returns current user when cookie present.
- Rotation on old sessions; no rotation on recent sessions.

Checks

- Cookie attributes (HttpOnly, SameSite, Secure as configured).
- Old sessions get rotated and persisted; new token set.
