### Playbook: WebAuthn / Passkeys

Golden path

- Registration: start -> finish, store credential (id, public key, transports)
- Authentication: start -> finish, increment sign counter

Error paths

- Invalid challenge, wrong origin/rpId, re-registration attempts

No-mock

- One end-to-end registration path without mocking verification where feasible (or as
  close as practical)
