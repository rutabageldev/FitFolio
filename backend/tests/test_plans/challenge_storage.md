# Test plan migrated: WebAuthn Challenge Storage

Challenge storage planning is part of Auth (WebAuthn):

- Domain doc: `docs/testing/domains/auth.md`
- Catalog: `docs/testing/catalog/auth.yaml`

Implement tests under `backend/tests/auth/webauthn/**`.

### Function: cleanup_expired_challenges(user_email, challenge_type)

#### Happy Path

- [ ] **Deletes keys for user/type pattern** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** Deletes keys where value starts with `${email}:`, returns count

- [ ] **No matches returns 0** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** low
  - **Expected:** Returns 0 without error

#### Error Handling

- [ ] **Scan/get failure raises RuntimeError** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** medium
  - **Expected:** Wrap and raise RuntimeError on scan_iter/get/delete failure

## Implementation Notes

- Use Redis test DB (fixtures already flush DB between tests).
- For opaque ID checks, assert length/charset, not specific format.
- Ensure single-use behavior by verifying key deletion after retrieval.
