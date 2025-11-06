# Test Plan: API Dependencies (deps.py)

**Module Path:** `app/api/deps.py`
**Test File:** `tests/test_deps.py`
**Current Coverage:** 100.00% (35/35 lines) ✅ TARGET EXCEEDED
**Target Coverage:** 85%+

## Overview

Tests for session management dependency injection functions used across all API endpoints.

## Test Cases

### Function: get_current_session_with_rotation()

#### Authentication Failures
- [x] **No token provided** - ✅ Implemented
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** HTTPException 401 "Not authenticated"

- [x] **Invalid token format** - ✅ Implemented
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** HTTPException 401 "Invalid or expired session"

- [x] **Expired session token** - ✅ Implemented
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** HTTPException 401 "Invalid or expired session"

- [x] **Revoked session token** - ✅ Implemented
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** HTTPException 401 "Invalid or expired session"

- [x] **Already rotated session token** - ✅ Implemented
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** HTTPException 401 "Invalid or expired session"

#### User Account Status
- [x] **Inactive user account** - ✅ Implemented
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** HTTPException 401 "User account is inactive"

- [ ] **Unverified email (if required)** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** HTTPException 403 or allow based on endpoint requirements

#### Session Rotation Logic
- [x] **Recent valid session (no rotation needed)** - ✅ Implemented
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return session and user, no cookie set

- [x] **Old session triggers rotation (>7 days)** - ✅ Implemented
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** New session created, old marked as rotated, new cookie set

- [ ] **Session at rotation boundary (exactly 7 days)** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** Verify rotation logic boundary condition

#### Cookie Security
- [x] **COOKIE_SECURE=true sets secure flag** - ✅ Implemented
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Cookie has Secure flag

- [ ] **COOKIE_SECURE=false omits secure flag** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** Cookie lacks Secure flag (dev only)

- [ ] **Cookie httponly flag always set** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Cookie has HttpOnly flag

- [ ] **Cookie samesite attribute set** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Cookie has SameSite=Lax or Strict

#### Concurrent Access
- [ ] **Concurrent requests with same token** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** Handle gracefully, avoid duplicate sessions

- [ ] **Token reuse after rotation** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** high
  - **Expected:** Reject old token after rotation

### Function: get_optional_session_with_rotation()

#### No Authentication
- [x] **No token returns None** - ✅ Implemented
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return (None, None)

- [x] **Invalid token returns None** - ✅ Implemented
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return (None, None)

#### Valid Authentication
- [x] **Valid token returns session** - ✅ Implemented
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return (session, user)

- [ ] **Session rotation also works** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Old sessions rotate, new cookie set

### Function: get_db()

- [ ] **Returns database session** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Yield AsyncSession

- [ ] **Session cleanup on exit** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Session closed after request

- [ ] **Session cleanup on exception** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** Session closed even if exception raised

### Function: get_session_token()

- [ ] **Extract token from cookie** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return token string from ff_sess cookie

- [ ] **No cookie returns None** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return None

- [ ] **Malformed cookie returns None** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** Return None gracefully

## Coverage Goals

### Current State (45.71%)
- Basic authentication flows covered
- Session rotation logic covered
- Optional session variant covered

### To Reach 85%+
- [ ] Cover get_db() function (currently untested)
- [ ] Cover get_session_token() function (currently untested)
- [ ] Add cookie security flag tests
- [ ] Add edge cases for session rotation boundary
- [ ] Add concurrent access scenarios

## Implementation Notes

### Fixtures Used
- `db_session` - Database session for test setup
- `test_user` - Local fixture for creating test users
- `monkeypatch` - For environment variable testing

### Test Patterns
- Use `pytest.raises(HTTPException)` for authentication failures
- Create sessions with specific timestamps for rotation testing
- Use `response.headers.get("set-cookie")` to verify cookie setting

### Related Modules to Test Together
- `app/core/security.py` - Token generation/validation
- `app/core/session_rotation.py` - Rotation logic
- `app/db/models/auth.py` - Session and User models
