# Test Plan: Database Lifecycle and Engine

**Module Path:** `app/db/database.py`
**Test File:** `tests/test_database.py` (new)

**Current Coverage:** TBD
**Target Coverage:** 85%+

## Test Cases

### Function: get_db()

- [ ] **Yields AsyncSession** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** critical
  - **Expected:** Provides usable session for queries

- [ ] **Closes session on normal exit** - ⏳ Pending

  - **Type:** happy_path
  - **Priority:** high
  - **Expected:** Session closed after context exit

- [ ] **Closes session on exception** - ⏳ Pending
  - **Type:** error_path
  - **Priority:** high
  - **Expected:** Session closed even when exception occurs inside dependency

### Function: init_db()

- [ ] **Creates tables without error** - ⏳ Pending
  - **Type:** integration
  - **Priority:** medium
  - **Expected:** `Base.metadata.create_all` invoked; models usable

### Function: close_db()

- [ ] **Disposes engine** - ⏳ Pending
  - **Type:** happy_path
  - **Priority:** medium
  - **Expected:** Engine disposed; new session requires new connection

### Connection URL Handling

- [ ] **Converts postgresql:// to postgresql+psycopg://** - ⏳ Pending
  - **Type:** edge_case
  - **Priority:** high
  - **Expected:** Engine created with async driver when legacy URL provided

## Implementation Notes

- Use an isolated in-memory SQLite engine for lifecycle checks, or a temporary Postgres if needed.
- Monkeypatch environment variables to test URL conversion branch.
