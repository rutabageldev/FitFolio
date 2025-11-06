# Test Plan: Admin Endpoints (admin.py)

**Module Path:** `app/api/v1/admin.py`
**Test File:** `tests/test_admin.py`
**Current Coverage:** 75.68% (56/74 lines)
**Target Coverage:** 85%+

## Overview

Admin endpoints for audit log querying and system management. Currently requires authentication but lacks proper admin role enforcement (TODO in code).

## Test Cases

### Endpoint: GET /api/v1/admin/audit/events

#### Authentication & Authorization
- [ ] **Unauthenticated request** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** HTTPException 401

- [ ] **Inactive user** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** HTTPException 403 "Admin access required"

- [ ] **Active user (temporary admin check)** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return audit log entries

- [ ] **Admin role enforcement (future)** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Note:** Will need tests when proper admin role is added

#### Query Filtering
- [ ] **No filters (default query)** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return all events with pagination

- [ ] **Filter by user_id** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Return events only for specified user

- [ ] **Filter by event_type** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Return events only of specified type

- [ ] **Filter by start_date** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Return events after start_date

- [ ] **Filter by end_date** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Return events before end_date

- [ ] **Filter by date range (start + end)** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Return events within date range

- [ ] **Multiple filters combined** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Return events matching all filters

#### Input Validation
- [ ] **Invalid user_id format** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** HTTPException 400 "Invalid user_id format"

- [ ] **Invalid date format** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** FastAPI validation error

- [ ] **Page < 1** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** medium
  - **Expected:** FastAPI validation error

- [ ] **Page_size < 1** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** medium
  - **Expected:** FastAPI validation error

- [ ] **Page_size > 1000** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** medium
  - **Expected:** FastAPI validation error

#### Pagination
- [ ] **First page with results** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return page 1, has_more=true if more pages exist

- [ ] **Middle page** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Return correct offset results, has_more=true

- [ ] **Last page** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Return remaining results, has_more=false

- [ ] **Page beyond available results** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** Return empty entries, total still correct

- [ ] **Custom page_size** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** Return correct number of items

#### Response Data
- [ ] **Event with associated user** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Include user_email in response

- [ ] **Event without user (null user_id)** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** user_id=null, user_email=null

- [ ] **Total count matches filtered results** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** total field is accurate count

- [ ] **Events ordered by created_at desc** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Most recent events first

### Endpoint: GET /api/v1/admin/audit/event-types

#### Authentication & Authorization
- [ ] **Unauthenticated request** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** HTTPException 401

- [ ] **Inactive user** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** HTTPException 403 "Admin access required"

- [ ] **Active user (authenticated)** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Return event types list

#### Response Data
- [ ] **Return distinct event types** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** List of unique event type strings

- [ ] **Event types sorted alphabetically** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** event_types in alphabetical order

- [ ] **Empty database returns empty list** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** low
  - **Expected:** {"event_types": []}

## Coverage Goals

### Current State (75.68%)
- Basic endpoint structure covered by existing tests
- Some authentication paths likely covered

### To Reach 85%+
- [ ] Add comprehensive filter testing
- [ ] Add pagination edge cases
- [ ] Add input validation tests
- [ ] Add response data verification
- [ ] Add event-types endpoint tests

## Implementation Notes

### Fixtures Needed
- `db_session` - Database session
- `client` - HTTP client for endpoint testing
- `test_user` - Authenticated active user
- `test_inactive_user` - Inactive user for 403 tests
- `test_login_events` - Sample audit log entries
- `auth_headers` - Function to generate auth cookies

### Test Data Setup
- Create multiple login events with different:
  - user_ids (some null)
  - event_types (variety for filtering)
  - timestamps (for date filtering)
  - Associated users (for join testing)

### Test Patterns
- Use `client.get()` with authenticated cookies
- Verify response status codes
- Verify response JSON structure matches Pydantic models
- Test pagination with known data sets
- Verify SQL query filtering logic

### Related Modules
- `app/db/models/auth.py` - LoginEvent model
- `app/api/deps.py` - Authentication dependency
- Tests in `test_audit_logging.py` may already cover some LoginEvent creation
