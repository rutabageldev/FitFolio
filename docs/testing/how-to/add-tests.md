### How to add tests

When

- Adding new endpoints or changing public behavior.
- Fixing a bug (add a failing test first).

Steps

1. Select level and bucket
   - Unit vs integration; place under `backend/tests/<bucket>/...`.
2. Name clearly
   - File/function names describe behavior, not implementation.
3. Mark appropriately
   - `@pytest.mark.unit` or `@pytest.mark.integration` (+ `@pytest.mark.security` when
     applicable).
4. Use fixtures
   - Reuse `conftest.py` fixtures; create domain fixtures only if necessary.
5. Minimize mocking
   - Mock only true external I/O; keep one no-mock path for critical flows.
6. Keep tests deterministic
   - Control time, randomness, and environment via fixtures.
7. Run locally and via pre-commit
   - `pre-commit run -a` before pushing.

Definition of Done

- Tests pass locally and in CI.
- Coverage not decreased for touched modules.
- Docs updated if public behavior changed.
