### Naming and structure

Layout (backend)

- Buckets: `backend/tests/{auth,security,admin,deps,contract}/`
- Colocate sub-domains: e.g., `auth/{email,magic_link,sessions,webauthn}/`
- Shared fixtures in `backend/tests/conftest.py`

Naming

- Files: `test_<domain>_<behavior>.py`
- Tests: `test_<condition>_<expected_behavior>`
- Classes: `Test<Subject>` used sparingly for grouping

Markers

- Use from `pytest.ini`: `unit`, `integration`, `security`, `contract`, `admin`, `slow`

Redundancy policy

- Remove 100% duplicates; prefer parametrization over copy-paste variants.
