### Writing contract tests

Purpose

- Prevent breaking changes to public API paths and shapes.

Scope

- Existence and versioning of endpoints (`/api/v1/...`).
- Basic unauthenticated status codes; do not overfit behavior.
- Keep domain/business assertions in domain tests.

Practices

- Use parametric inventories for paths and methods.
- Fail on 404; warn (log) on unexpected status where appropriate.
- Keep files under `backend/tests/contract/`.
- Mark with `@pytest.mark.contract` and `@pytest.mark.integration`.
