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

- [ ] **List active sessions** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, list of sessions with current session marked

#### Error Handling

- [ ] **Unauthenticated request** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

### Endpoint: DELETE /api/v1/auth/sessions/{session_id}

#### Happy Path

- [ ] **Revoke specific session** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, session revoked

#### Error Handling

- [ ] **Unauthenticated request** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

- [ ] **Revoke own current session** - ⏳ Pending

  - **Type:** edge_case
  - **Priority:** high
  - **Expected:** 400 "Cannot revoke current session"

- [ ] **Revoke session belonging to another user** - ⏳ Pending

  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 404 not found (security: don't reveal existence)

- [ ] **Session already revoked** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** 404 or 200 idempotent

### Endpoint: DELETE /api/v1/auth/sessions/others

#### Happy Path

- [ ] **Revoke all other sessions** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, count of revoked sessions

- [ ] **No other sessions to revoke** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** 200, revoked_count=0

#### Error Handling

- [ ] **Unauthenticated request** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

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

## Recent Progress (2025-11-11)

### Session 1: Error Path Tests (26 tests in test_auth_error_paths.py)

#### Completed Tests

**WebAuthn Registration Errors (5 tests):**
- ✅ Redis challenge storage failure
- ✅ Malformed credential data
- ✅ User not found during registration
- ✅ Invalid/expired challenge
- ✅ Challenge email mismatch

**WebAuthn Authentication Errors (8 tests):**
- ✅ User not found
- ✅ No passkeys registered
- ✅ Redis challenge storage failure
- ✅ Invalid challenge
- ✅ Missing credential ID
- ✅ Credential not found
- ✅ Malformed credential

**Magic Link Errors (6 tests):**
- ✅ Email send failure (SMTP)
- ✅ New user verification flow
- ✅ Existing verified user login flow
- ✅ Inactive user rejection
- ✅ Unverified email rejection
- ✅ Account lockout enforcement

**Email Verification Errors (3 tests):**
- ✅ Invalid token
- ✅ Inactive user
- ✅ Wrong token purpose

**Resend Verification Errors (4 tests):**
- ✅ Email send failure
- ✅ Successful resend
- ✅ Already verified (no email sent)
- ✅ Non-existent user (enumeration protection)

#### Error Handling Improvements Added to auth.py

- Added try-catch for Redis challenge storage failures (2 locations)
- Added try-catch for email send failures (3 locations)
- Fixed bug: user creation missing timestamps

#### Coverage Impact

- **auth.py:** 41.03% → 48.13% (+7.1 percentage points)
- **Lines covered:** 167 → 206 (+39 lines)
- **Lines remaining:** 240 → 222 (-18 lines)

---

### Session 2: Authorization Tests (14 tests in test_auth_authorization.py)

#### Completed Tests

**WebAuthn Authorization (4 tests):**
- ✅ Registration start CSRF protection
- ✅ Registration finish CSRF protection
- ✅ Authentication start CSRF protection
- ✅ Authentication finish CSRF protection

**Credential Management Authorization (2 tests):**
- ✅ List credentials requires authentication
- ✅ Delete credential requires authentication

**Session Management Authorization (3 tests):**
- ✅ List sessions requires authentication
- ✅ Revoke session requires authentication
- ✅ Revoke all other sessions requires authentication

**User Endpoints Authorization (1 test):**
- ✅ /me endpoint requires authentication

**Public Endpoints Verification (4 tests):**
- ✅ Magic link start is public (no CSRF required)
- ✅ Magic link verify has CSRF protection
- ✅ Email verify has CSRF protection
- ✅ Resend verification is public (no CSRF required)

#### Coverage Impact

- **Overall backend:** 72.08% (no change - authorization tests cover existing code paths)
- **auth.py:** 48.13% (no change - validates existing security controls)

---

### Combined Progress Summary

**Total Tests Added:** 40 tests (26 error paths + 14 authorization)
**Coverage Achieved:**
- Overall: 70.78% → 72.08% (+1.3%)
- auth.py: 41.03% → 48.13% (+7.1%)

**Remaining Work to 85%:**
- Need +36.87% more coverage in auth.py
- Estimated ~158 more lines to cover
- Focus areas: happy paths, session management, WebAuthn success flows
