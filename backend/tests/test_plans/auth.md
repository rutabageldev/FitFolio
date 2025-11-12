# Test Plan: Authentication Endpoints (auth.py)

**Module Path:** `app/api/v1/auth.py`
**Test File:** `tests/test_auth_endpoints.py`, `tests/test_auth_error_paths.py`
**Current Coverage:** 48.13% (206/428 lines) - Updated 2025-11-11
**Target Coverage:** 85%+

## Overview

Complete authentication flow endpoints for magic link, WebAuthn, email verification, and session management. This is the largest untested module with **222 missing lines** (down from 240).

**Note:** Some auth flows are already tested in existing test files (test_magic_link.py, test_webauthn.py, etc.), but endpoint-level testing is insufficient.

## Test Cases

### Endpoint: POST /api/v1/auth/magic-link/start

#### Happy Path

- [x] **Valid email sends magic link** - ✅ Partial (test_magic_link.py)

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, email sent, token stored

- [ ] **Unverified user can request magic link** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** 200, magic link sent

#### Rate Limiting

- [ ] **Respects rate limit decorator** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 429 after exceeding limit

#### Error Handling

- [ ] **Invalid email format** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 422 validation error

- [ ] **Empty email** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 422 validation error

- [x] **SMTP failure (email can't send)** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 500 or handle gracefully
  - **Test:** `test_magic_link_start_email_failure`

- [ ] **Database connection failure** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 500 internal server error

#### Security/Privacy

- [ ] **Unknown email returns generic success (no enumeration)** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200 with generic message, no disclosure whether user exists

- [x] **New email triggers verification flow (not login)** - ✅ Complete (test_auth_error_paths.py)
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** `magic_link_tokens.purpose="email_verification"`, email content points to verification URL
  - **Test:** `test_magic_link_start_creates_user_and_sends_verification`

### Endpoint: POST /api/v1/auth/magic-link/verify

#### Happy Path

- [x] **Valid token creates session** - ✅ Partial (test_magic_link.py)

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, session cookie set

- [ ] **Token used for new user creates account** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** User created, session set

- [ ] **Token used for existing user logs in** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Session created, no duplicate user

#### Rate Limiting

- [ ] **Respects rate limit decorator** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 429 after exceeding limit

#### Error Handling

- [ ] **Invalid token format** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid or expired token"

- [ ] **Expired token** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid or expired token"

- [ ] **Token not found in Redis** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid or expired token"

- [ ] **Used/consumed token** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid or expired token"

- [x] **Inactive user** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Account is inactive"
  - **Test:** `test_magic_link_verify_inactive_user`

- [x] **Account locked (too many failed attempts)** - ✅ Complete (test_auth_error_paths.py)
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 429 "Account temporarily locked"
  - **Test:** `test_magic_link_verify_account_locked`

#### Security

- [x] **Unverified user cannot login** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 403 with verification-required message
  - **Test:** `test_magic_link_verify_unverified_email`

- [ ] **Sets cookie with correct flags** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** `HttpOnly` set; `Secure` depends on env; `SameSite=Lax`

### Endpoint: POST /api/v1/auth/webauthn/register/start

#### Happy Path

- [ ] **Authenticated user starts registration** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, registration options with challenge

- [ ] **Exclude existing credentials** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Options include existing credential IDs in excludeCredentials

#### Additional Behavior

- [ ] **Non-existent user email creates user record** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** User auto-created prior to registration flow

#### Error Handling

- [ ] **Unauthenticated request** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

- [ ] **Inactive user** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 or 403

- [x] **Redis challenge storage failure** - ✅ Complete (test_auth_error_paths.py)
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 500 internal server error
  - **Test:** `test_register_start_redis_failure`

### Endpoint: POST /api/v1/auth/webauthn/register/finish

#### Happy Path

- [ ] **Valid credential registration** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, credential stored in database

- [ ] **First credential for user** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Credential created with is_primary=true

- [ ] **Additional credential for user** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Credential created, is_primary=false

#### Error Handling

- [x] **User not found** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 404 "User not found"
  - **Test:** `test_register_finish_user_not_found`

- [ ] **Unauthenticated request** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

- [x] **Challenge not found (expired or missing)** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Challenge expired"
  - **Test:** `test_register_finish_invalid_challenge`

- [x] **Challenge mismatch** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid credential"
  - **Test:** `test_register_finish_challenge_email_mismatch`

- [x] **WebAuthn verification fails** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid credential"
  - **Test:** `test_register_finish_malformed_credential`

- [ ] **Duplicate credential ID** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 409 conflict or handle gracefully

### Endpoint: POST /api/v1/auth/webauthn/authenticate/start

#### Happy Path

- [ ] **User with credentials starts authentication** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, authentication options with allowCredentials

- [ ] **User without credentials (discoverable)** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** 200, empty allowCredentials (platform authenticator)

#### Rate Limiting

- [ ] **Respects rate limit decorator** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 429 after exceeding limit

#### Error Handling

- [ ] **Invalid email format** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 422 validation error

- [x] **User not found** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 404 not found (current behavior)
  - **Test:** `test_authenticate_start_user_not_found`

- [ ] **Enumeration-resistant response (future)** - ⏳ Pending (future functionality)

  - **Type:** error_path
  - **Priority:** medium
  - **Expected:** Return generic 200 without disclosing existence (to be implemented)

- [x] **User with no credentials** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 400 "No passkeys registered"
  - **Test:** `test_authenticate_start_no_credentials`

- [x] **Redis challenge storage failure** - ✅ Complete (test_auth_error_paths.py)
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 500 internal server error
  - **Test:** `test_authenticate_start_redis_failure`

### Endpoint: POST /api/v1/auth/webauthn/authenticate/finish

#### Happy Path

- [ ] **Valid authentication creates session** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, session cookie set

- [ ] **Sign count updated** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Credential sign_count incremented

#### Rate Limiting

- [ ] **Respects rate limit decorator** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 429 after exceeding limit

#### Error Handling

- [x] **User not found** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 404 "User not found"
  - **Test:** `test_authenticate_finish_user_not_found`

- [x] **Challenge not found** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Challenge expired"
  - **Test:** `test_authenticate_finish_invalid_challenge`

- [x] **Credential ID missing** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Credential ID is required"
  - **Test:** `test_authenticate_finish_missing_credential_id`

- [x] **Credential not found** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid credential"
  - **Test:** `test_authenticate_finish_credential_not_found`

- [x] **WebAuthn verification fails** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid credential"
  - **Test:** `test_authenticate_finish_malformed_credential`

- [ ] **Account locked** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 403 "Account temporarily locked"

- [ ] **Inactive user** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 or 403

#### Cookies & Headers

- [ ] **Cookie flags set correctly** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** `HttpOnly` set; `Secure` based on env; `SameSite=Lax`

- [ ] **Rate limit headers present on success** - ⏳ Pending
  - **Type:** integration
  - **Priority:** medium
  - **Expected:** X-RateLimit-\* headers included when limiter applies

### Endpoint: GET /api/v1/auth/webauthn/credentials

#### Happy Path

- [ ] **List user's credentials** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, list of credentials (no public key exposed)

- [ ] **Empty list for user with no credentials** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** 200, empty array

#### Error Handling

- [ ] **Unauthenticated request** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

### Endpoint: POST /api/v1/auth/logout

#### Happy Path

- [ ] **Authenticated logout revokes session** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, session revoked, cookie cleared

#### Error Handling

- [ ] **Unauthenticated request still returns 200** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** 200, no-op (idempotent)

- [ ] **Already logged out (double logout)** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** 200, idempotent

### Endpoint: GET /api/v1/auth/me

#### Happy Path

- [ ] **Authenticated user gets info** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, user object

- [ ] **Auto session rotation after 7 days** - ⏳ Pending
  - **Type:** integration
  - **Priority:** high
  - **Expected:** New session created; cookie updated; old marked rotated

#### Error Handling

- [ ] **Unauthenticated request** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

- [ ] **Inactive user** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401

### Endpoint: POST /api/v1/auth/email/verify

#### Happy Path

- [ ] **Valid verification token verifies email** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, is_email_verified=true

#### Error Handling

- [ ] **Unauthenticated request** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

- [x] **Invalid token** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid or expired token"
  - **Test:** `test_email_verify_invalid_token`

- [x] **Inactive user** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Account is inactive"
  - **Test:** `test_email_verify_inactive_user`

- [x] **Wrong token purpose** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid or expired token"
  - **Test:** `test_email_verify_wrong_purpose`

- [ ] **Already verified email** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** low
  - **Expected:** 200, idempotent

### Endpoint: POST /api/v1/auth/email/resend-verification

#### Happy Path

- [x] **Resend verification email** - ✅ Complete (test_auth_error_paths.py)
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, new email sent
  - **Test:** `test_resend_verification_success`

#### Rate Limiting

- [ ] **Respects rate limit decorator** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 429 after exceeding limit

#### Error Handling

- [ ] **Unauthenticated request** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

- [x] **Already verified email** - ✅ Complete (test_auth_error_paths.py)

  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** 200 "Email already verified" (no email sent)
  - **Test:** `test_resend_verification_already_verified_no_email`

- [x] **SMTP failure** - ✅ Complete (test_auth_error_paths.py)
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 500 or handle gracefully
  - **Test:** `test_resend_verification_email_failure`

#### Privacy

- [x] **No enumeration leakage in resend** - ✅ Complete (test_auth_error_paths.py)
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Generic 200 response whether email exists or not
  - **Test:** `test_resend_verification_nonexistent_user_no_email`

### Endpoint: GET /api/v1/auth/sessions

#### Happy Path

- [x] **List active sessions** - ✅ Complete (test_auth_session_management.py)
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, list of sessions with current session marked
  - **Test:** `test_list_sessions_single`, `test_list_sessions_multiple`

- [x] **Exclude revoked sessions** - ✅ Complete (test_auth_session_management.py)
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Only active sessions returned
  - **Test:** `test_list_sessions_excludes_revoked`

#### Error Handling

- [x] **Unauthenticated request** - ✅ Complete (test_auth_session_management.py)
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized
  - **Test:** `test_list_sessions_unauthenticated`

### Endpoint: DELETE /api/v1/auth/sessions/{session_id}

#### Happy Path

- [x] **Revoke specific session** - ✅ Complete (test_auth_session_management.py)
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, session revoked
  - **Test:** `test_revoke_other_session`

#### Error Handling

- [x] **Revoke own current session** - ✅ Complete (test_auth_session_management.py)

  - **Type:** edge_case
  - **Priority:** high
  - **Expected:** 400 "Cannot revoke current session"
  - **Test:** `test_revoke_current_session_rejected`

- [x] **Revoke session belonging to another user** - ✅ Complete (test_auth_session_management.py)

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 404 not found (security: don't reveal existence)
  - **Test:** `test_revoke_session_of_other_user`

- [x] **Session already revoked** - ✅ Complete (test_auth_session_management.py)
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** 404 idempotent
  - **Test:** `test_revoke_already_revoked_session`

- [x] **Nonexistent session** - ✅ Complete (test_auth_session_management.py)
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 404 not found
  - **Test:** `test_revoke_nonexistent_session`

### Endpoint: POST /api/v1/auth/sessions/revoke-all-others

#### Happy Path

- [x] **Revoke all other sessions** - ✅ Complete (test_auth_session_management.py)

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, count of revoked sessions
  - **Test:** `test_revoke_all_others_success`

- [x] **No other sessions to revoke** - ✅ Complete (test_auth_session_management.py)
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** 200, revoked_count=0
  - **Test:** `test_revoke_all_others_no_other_sessions`

#### Error Handling

- [x] **Unauthenticated request** - ✅ Complete (test_auth_session_management.py)
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized
  - **Test:** `test_revoke_all_others_unauthenticated`

## Coverage Goals

### Current State (41.03%)

- Basic happy paths partially covered in separate test files
- Most error paths untested
- Rate limiting not tested
- Edge cases not covered

### To Reach 85%+

- [ ] Add comprehensive error path testing for all endpoints
- [ ] Add rate limiting tests for protected endpoints
- [ ] Add edge case tests (double logout, already verified, etc.)
- [ ] Add SMTP failure handling tests
- [ ] Add database failure tests
- [ ] Add Redis failure tests
- [ ] Add account lockout integration tests

## Implementation Notes

### Fixtures Needed

- `client` - HTTP client for endpoint testing
- `db_session` - Database session
- `test_user` - Authenticated user
- `test_inactive_user` - Inactive user
- `auth_cookie` - Function to generate auth cookies
- `mock_email` - Mock email sending
- `redis_client` - For challenge storage tests

### Test Data Setup

- Create test users with various states (active, inactive, verified, unverified)
- Create WebAuthn credentials for users
- Store challenges in Redis for WebAuthn flows
- Create magic link tokens

### Test Patterns

- Use `client.post()` / `client.get()` / `client.delete()`
- Verify response status codes
- Verify response JSON matches Pydantic models
- Verify database state changes (user created, session created, etc.)
- Verify Redis state (challenges stored/consumed)
- Mock external dependencies (email sending)

### Related Modules

- Tests already exist: test_magic_link.py, test_webauthn.py, test_email_verification.py, test_session_management.py
- Need to consolidate or add endpoint-level tests in test_auth_endpoints.py
- Consider refactoring to avoid duplication

### Critical Security Tests

- Account lockout enforcement
- Rate limiting effectiveness
- Session security (HTTPOnly, Secure flags)
- Token expiration and invalidation
- User enumeration prevention
- CSRF protection (covered by middleware)

## Recent Progress

### Session 1: Error Paths (2025-11-11)
- Created test_auth_error_paths.py with 26 comprehensive error tests
- Added infrastructure failure handling in auth.py endpoints
- Fixed bug: missing timestamps in user creation
- Coverage: 41.03% → 48.13%

### Session 2: Authorization (2025-11-11)
- Created test_auth_authorization.py with 14 CSRF and authentication tests
- Validated security boundaries across all endpoints
- Coverage: 48.13% (maintained)

### Session 3: Happy Paths (2025-11-12)
- Created test_auth_webauthn_happy_paths.py with 7 WebAuthn happy path tests
- Created test_auth_magic_link_happy_paths.py with 11 magic link happy path tests
- Fixed 3 production bugs discovered during testing
- Coverage: 48.13% → 52%

### Session 4: User-Facing Endpoints (2025-11-12)
- Created test_auth_user_endpoints.py with 9 user-facing endpoint tests
- Tests for /me, /logout, /webauthn/credentials, /email/verify
- Validated authentication methods (cookie-based vs Bearer token)
- Coverage: 52% (maintained, ~45 total auth tests implemented)

### Session 5: Session Management (2025-11-12)
- Created test_auth_session_management.py with 12 session management tests
- Tests for GET /sessions, DELETE /sessions/{id}, POST /sessions/revoke-all-others
- Validated security boundaries (no cross-user enumeration, current session protection)
- Coverage: 52% (maintained, ~57 total auth tests implemented)
