# Test Plan: Request ID Middleware

**Module Path:** `app/middleware/request_id.py`
**Test File:** `tests/test_request_id.py` (new)

**Current Coverage:** 100.00% (per index)
**Target Coverage:** 100% (small module)

## Test Cases

### Class: RequestIDMiddleware

#### Happy Path
- [ ] **Generates UUID when header missing** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** Response has `x-request-id` header; value matches UUID format

- [ ] **Echoes incoming x-request-id** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Response `x-request-id` equals request header value

#### Context Binding
- [ ] **Clears bound context after request** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** low
  - **Expected:** Subsequent request does not retain previous context (can assert by logging/mocking bind/clear)

## Implementation Notes
- For context verification, monkeypatch `bind_ctx`/`clear_ctx` to record calls.
- Validate presence and propagation of header across a simple test route (e.g., `/healthz`).
