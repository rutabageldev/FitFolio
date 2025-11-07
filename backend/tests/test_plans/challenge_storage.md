# Test Plan: WebAuthn Challenge Storage (Redis)

**Module Path:** `app/core/challenge_storage.py`
**Test File:** `tests/test_challenge_storage.py` (new)

**Current Coverage:** TBD
**Target Coverage:** 90%+ (security-critical)

## Test Cases

### Function: store_challenge(user_email, challenge_hex, challenge_type)

#### Happy Path

- [ ] **Stores challenge with TTL** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Key `webauthn:challenge:{type}:{id}` set with TTL=60, value `${email}:${hex}`

- [ ] **Returns opaque challenge_id** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** `challenge_id` is unguessable-looking (length check)

#### Error Handling

- [ ] **Redis error raises RuntimeError** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Wrap and raise RuntimeError on setex failure

### Function: retrieve_and_delete_challenge(challenge_id, challenge_type)

#### Happy Path

- [ ] **Gets and deletes single-use challenge** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Returns (email, hex), key removed

- [ ] **Missing/expired challenge returns None** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Returns None when key absent

#### Malformed Data

- [ ] **Malformed stored value returns None** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** Value without separator handled gracefully

#### Error Handling

- [ ] **Redis error raises RuntimeError** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** Wrap and raise RuntimeError on pipeline failure

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
