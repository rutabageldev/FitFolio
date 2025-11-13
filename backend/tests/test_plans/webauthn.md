# Test plan migrated: WebAuthn

WebAuthn planning is part of Auth:

- Domain doc: `docs/testing/domains/auth.md`
- Catalog: `docs/testing/catalog/auth.yaml`

Implement tests under `backend/tests/auth/webauthn/**`.

- **Type:** happy_path
- **Priority:** high
- **Expected:** Empty exclude_credentials list

- [ ] **Exclude existing credentials** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Convert credential dicts to PublicKeyCredentialDescriptor

- [ ] **Exclude credentials with transports** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Include transport information if provided

- [ ] **Exclude credentials without transports** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** Handle missing transports gracefully

#### Error Handling

- [ ] **Invalid user_id format** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** high
  - **Expected:** Raise appropriate error or handle gracefully

- [ ] **Invalid exclude_credentials format** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** high
  - **Expected:** Raise ValueError or handle gracefully

- [ ] **Malformed credential ID in exclude** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** Raise ValueError with clear message

### Function: generate_authentication_options()

#### Happy Path

- [ ] **Generate basic authentication options** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return PublicKeyCredentialRequestOptions with challenge

- [ ] **No allow_credentials (passwordless)** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Empty allow_credentials list

- [ ] **Allow specific credentials** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Convert credential dicts to PublicKeyCredentialDescriptor

- [ ] **Allow credentials with transports** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Include transport information if provided

#### Error Handling

- [ ] **Invalid allow_credentials format** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** high
  - **Expected:** Raise ValueError or handle gracefully

- [ ] **Malformed credential ID in allow** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** Raise ValueError with clear message

### Function: verify_registration_response()

#### Happy Path

- [ ] **Verify valid registration response** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return dict with credential_id, public_key, sign_count

- [ ] **Extract authenticator data flags** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Include backed_up, uv_available flags

- [ ] **Include transports in response** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Return transports from credential response

#### Error Handling

- [ ] **Invalid credential response** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError "WebAuthn registration verification failed"

- [ ] **RP ID mismatch** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError with verification failure message

- [ ] **Origin mismatch** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError with verification failure message

- [ ] **Challenge mismatch** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError with verification failure message

- [ ] **Malformed credential data** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** Raise ValueError with wrapped exception

### Function: verify_authentication_response()

#### Happy Path

- [ ] **Verify valid authentication response** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return dict with new_sign_count, user_verified

- [ ] **Sign count incremented** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** new_sign_count > credential_current_sign_count

- [ ] **User verified flag** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** user_verified reflects authenticator UV flag

#### Error Handling

- [ ] **Invalid credential response** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError "WebAuthn authentication verification failed"

- [ ] **RP ID mismatch** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError with verification failure message

- [ ] **Origin mismatch** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError with verification failure message

- [ ] **Challenge mismatch** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError with verification failure message

- [ ] **Invalid public key** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError with verification failure message

- [ ] **Sign count not incremented (potential cloning)** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError or flag security issue

- [ ] **Replay attack (same challenge reused)** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Raise ValueError with verification failure

### Function: get_webauthn_manager()

- [ ] **Load from environment variables** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Return WebAuthnManager with env config

- [ ] **Use default values if env vars missing** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** Return WebAuthnManager with defaults (RP_NAME="FitFolio", etc.)

- [ ] **Custom environment variables** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** Respect RP_NAME, RP_ID, RP_ORIGIN env vars

### Integration with Endpoints (Notes)

- [ ] **Registration start creates user if not exists** - ⏳ Pending

  - **Type:** integration
  - **Priority:** medium
  - **Expected:** When called via endpoint with unknown email, user is created (matches current implementation)

- [ ] **Enumeration-resistant auth start (future)** - ⏳ Pending (future functionality)
  - **Type:** error_path
  - **Priority:** medium
  - **Expected:** Return generic success even if user not found (will require endpoint changes)

## Coverage Goals

### Current State (58.14%)

- Basic happy path likely covered
- Some conversion logic tested

### To Reach 85%+

- [ ] Add comprehensive error path testing for verification failures
- [ ] Add malformed input handling tests
- [ ] Add edge cases for credential descriptors
- [ ] Add authenticator data flag tests
- [ ] Add environment configuration tests

## Implementation Notes

### Fixtures Needed

- `webauthn_manager` - WebAuthnManager instance
- `mock_registration_credential` - Valid registration response
- `mock_authentication_credential` - Valid authentication response
- `test_challenge` - 32-byte challenge
- `monkeypatch` - For environment variable testing

### Test Patterns

- Use `pytest.raises(ValueError)` for verification failures
- Mock webauthn library functions for isolated unit tests
- Verify error messages contain "WebAuthn ... verification failed"
- Test both happy path and error conditions for each function

### Related Modules

- `app/api/v1/auth.py` - WebAuthn endpoint usage
- `app/db/models/auth.py` - WebAuthnCredential model
- External: `webauthn` library (py_webauthn)

### Security Considerations

- Challenge uniqueness and expiration
- Replay attack prevention
- Sign count validation for cloned credential detection
- RP ID and origin validation
- User verification requirements
