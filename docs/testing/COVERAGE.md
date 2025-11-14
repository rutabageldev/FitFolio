# Test Coverage Guide

## Overview

FitFolio maintains a **minimum 85% test coverage** requirement for the backend,
currently at **94.37%**.

## Coverage Enforcement

### Local Development

Coverage is automatically checked when running tests:

```bash
# Run tests with coverage (enforces 85% minimum)
cd backend && pytest

# Or use make
make test
```

If coverage falls below 85%, pytest will fail with:

```
FAIL Required test coverage of 85% not reached. Total coverage: XX.XX%
```

### CI/CD Pipeline

The CI workflow ([.github/workflows/ci.yml](../../.github/workflows/ci.yml)) enforces
coverage on every push and PR:

1. **Tests run** with coverage collection
2. **Build fails** if coverage < 85%
3. **Coverage artifacts** are uploaded (HTML report, XML, .coverage)
4. **PR comment** shows coverage percentage with color-coded emoji:
   - 🟢 >= 90% (excellent)
   - 🟡 >= 85% (meets requirement)
   - 🔴 < 85% (fails)

## Coverage Reports

### Viewing Coverage Locally

After running tests, open the HTML report:

```bash
cd backend
pytest
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Viewing Coverage in CI

1. Go to the **Actions** tab in GitHub
2. Click on a workflow run
3. Scroll to **Artifacts** section
4. Download `backend-coverage-report`
5. Extract and open `htmlcov/index.html`

## Coverage Badge

The README displays a live coverage badge that updates automatically after each push to
main:

[![Coverage](https://img.shields.io/badge/coverage-94.4%25-brightgreen)]()

**Badge colors:**

- `brightgreen` (>= 90%)
- `green` (>= 85%)
- `yellow` (>= 80%)
- `orange` (>= 70%)
- `red` (< 70%)

The badge is automatically updated by the
[update-coverage-badge workflow](../../.github/workflows/update-coverage-badge.yml).

## Configuration

### pytest.ini

```ini
addopts =
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=85
```

### CI Workflow

```yaml
- name: Run tests with coverage
  run: |
    pytest --cov=app --cov-report=xml --cov-report=html --cov-report=term --cov-fail-under=85
```

## Best Practices

### Writing Tests for Coverage

1. **Test all code paths**: If/else branches, error handlers, edge cases
2. **Focus on critical paths**: Authentication, authorization, data validation
3. **Mock external dependencies**: Redis, databases, email services
4. **Use pytest markers**: `@pytest.mark.unit`, `@pytest.mark.integration`

### Current Coverage by Module

| Module                 | Coverage | Status |
| ---------------------- | -------- | ------ |
| `app/api/deps.py`      | 100%     | ✅     |
| `app/core/security.py` | 97.78%   | ✅     |
| `app/middleware/`      | 97.50%+  | ✅     |
| `app/api/v1/auth.py`   | 89.71%   | ✅     |
| `app/api/v1/admin.py`  | 86.49%   | ✅     |
| `app/db/database.py`   | 88.24%   | ✅     |

### Improving Coverage

If coverage drops below 85%:

1. **Identify uncovered lines**:

   ```bash
   pytest --cov=app --cov-report=term-missing
   ```

2. **Check HTML report** for visual coverage:

   ```bash
   pytest && open htmlcov/index.html
   ```

3. **Add targeted tests** for uncovered lines

4. **Verify improvement**:
   ```bash
   pytest --cov=app --cov-report=term
   ```

## Exceptions

Some code is intentionally excluded from coverage:

- **Debug endpoints** (dev-only routes)
- **Type stubs** (`.pyi` files)
- **Abstract base classes** (unreachable code)

Configure exclusions in `pyproject.toml`:

```toml
[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/migrations/*"
]
```

## Troubleshooting

### Coverage shows 0% or is incorrect

**Solution:** Clear coverage cache and re-run:

```bash
rm -rf .coverage htmlcov/
pytest
```

### Tests pass locally but fail in CI with coverage error

**Cause:** CI runs with stricter environment (no Redis/DB connection issues)

**Solution:**

1. Check CI logs for actual test failures
2. Ensure environment variables are set correctly
3. Use `conftest.py` auto-detection instead of manual env vars

### Badge not updating

**Cause:** The badge update workflow runs after CI completes on main

**Solution:**

1. Check
   [update-coverage-badge workflow](../../.github/workflows/update-coverage-badge.yml)
2. Ensure `contents: write` permission is granted
3. Badge updates within ~1 minute of CI completion

## Related Documentation

- [Testing Guide](./README.md)
- [Test Catalog](./catalog/)
- [CI/CD Pipeline](../../.github/workflows/ci.yml)
