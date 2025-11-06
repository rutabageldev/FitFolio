# Test Plan: Authentication Endpoints (auth.py)

**Module Path:** `app/api/v1/auth.py`
**Test File:** `tests/test_auth_endpoints.py` (new file, separate from test_auth.py)
**Current Coverage:** 41.03% (167/407 lines)
**Target Coverage:** 85%+

## Overview

Complete authentication flow endpoints for magic link, WebAuthn, email verification, and session management. This is the largest untested module with **240 missing lines**.

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

- [ ] **SMTP failure (email can't send)** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 500 or handle gracefully

- [ ] **Database connection failure** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 500 internal server error

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

- [ ] **Account locked (too many failed attempts)** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 403 "Account temporarily locked"

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

#### Error Handling
- [ ] **Unauthenticated request** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

- [ ] **Inactive user** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 or 403

- [ ] **Redis challenge storage failure** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 500 internal server error

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
- [ ] **Unauthenticated request** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 unauthorized

- [ ] **Challenge not found (expired or missing)** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Challenge expired"

- [ ] **Challenge mismatch** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid credential"

- [ ] **WebAuthn verification fails** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid credential"

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

- [ ] **User not found** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 200 (same as success to prevent enumeration)

- [ ] **Redis challenge storage failure** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 500 internal server error

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
- [ ] **Challenge not found** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Challenge expired"

- [ ] **Challenge mismatch** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid credential"

- [ ] **Credential not found** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid credential"

- [ ] **WebAuthn verification fails** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid credential"

- [ ] **Account locked** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 403 "Account temporarily locked"

- [ ] **Inactive user** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 401 or 403

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

- [ ] **Invalid token** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid or expired token"

- [ ] **Expired token** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 400 "Invalid or expired token"

- [ ] **Already verified email** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** low
  - **Expected:** 200, idempotent

### Endpoint: POST /api/v1/auth/email/resend-verification

#### Happy Path
- [ ] **Resend verification email** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200, new email sent

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

- [ ] **Already verified email** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** 400 "Email already verified"

- [ ] **SMTP failure** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** 500 or handle gracefully

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
