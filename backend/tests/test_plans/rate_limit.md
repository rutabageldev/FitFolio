# Test Plan: Rate Limiting (middleware + core)

**Module Paths:**
`app/middleware/rate_limit.py` (middleware)
`app/core/rate_limiter.py` (algorithm)

**Test Files:**
`tests/test_rate_limiting.py` (middleware)
`tests/test_rate_limiter.py` (new file for core)

**Current Coverage:** TBD
**Target Coverage:** 90%+ (security control)

## Test Cases

### Middleware: RateLimitMiddleware

#### Happy Path

- [ ] **Allowed request passes through** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** 200 response, X-RateLimit-\* headers present

- [ ] **Global fallback limit applied** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Matches `rl:global` when no specific pattern matches

#### Config and Exemptions

- [ ] **RATE_LIMIT_ENABLED=false disables checks** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** No X-RateLimit-\* headers added, no 429

- [ ] **Exempt paths bypass limiter** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Paths in `exempt_paths` not rate limited

- [ ] **Health endpoints bypass limiter** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** `/healthz` unaffected

#### Denials

- [ ] **Exceed per-endpoint limit returns 429** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** 429 with `Retry-After`, headers show Remaining=0

#### Headers

- [ ] **Headers reflect remaining and reset** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` set

#### Identification

- [ ] **IP-based identification with X-Forwarded-For** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** high
  - **Expected:** Uses first IP from `X-Forwarded-For`

### Core: RateLimiter (token bucket sliding window)

#### Happy Path

- [ ] **Within limit allowed and counted** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** `allowed=True`, `remaining` decrements, reset set

- [ ] **At limit denies and sets retry_after** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** critical
  - **Expected:** `allowed=False`, `retry_after>0`

#### Sliding Window Behavior

- [ ] **Old entries expire and allow new requests** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** high
  - **Expected:** After window elapses, requests allowed again

#### Concurrency

- [ ] **Pipeline atomicity prevents race conditions** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** medium
  - **Expected:** Concurrent calls do not exceed limit (simulate with awaitables)

#### Identifier Strategies (future)

- [ ] **User strategy uses request.state.user_id** - ⏳ Pending (future functionality)
  - **Type:** happy_path
  - **Priority:** medium
  - **Note:** Add tests once endpoints bind `request.state.user_id`

## Implementation Notes

- Use Redis test DB (`db=1`) and flush per test (fixtures exist).
- Mock time to test sliding window deterministically (e.g., freezegun or monkeypatch `time.time`).
- Validate headers in middleware path and raw results in core path.
