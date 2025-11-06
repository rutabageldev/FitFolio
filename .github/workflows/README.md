# GitHub Actions Workflows

This directory contains automated CI/CD workflows for FitFolio.

## Workflows

### `ci.yml` - Continuous Integration
**Triggers:** Pull requests, pushes to main

**Jobs:**
- `backend-tests` - Run pytest with PostgreSQL and Redis
- `backend-lint` - Ruff linting and formatting checks
- `backend-security` - Bandit and pip-audit scans
- `backend-migrations` - Alembic migration consistency check
- `frontend-lint` - ESLint and Prettier checks
- `frontend-build` - Vite production build verification
- `frontend-security` - npm audit for vulnerabilities
- `frontend-tests` - Vitest (optional, no tests yet)
- `ci-success` - Summary job for branch protection

**Runtime:** ~3-5 minutes

### `cd.yml` - Continuous Deployment
**Triggers:** Pushes to main (after CI passes)

**Jobs:**
- `build-backend` - Build and push backend Docker image
- `build-frontend` - Build and push frontend Docker image
- `update-compose` - Generate deployment instructions

**Output:**
- Images pushed to GitHub Container Registry (ghcr.io)
- Tagged with `latest` and `sha-{commit}`

## Local Testing

Before pushing, run checks locally to catch issues early:

### Backend
```bash
cd backend

# Run tests
pytest

# Run linting
ruff check .
ruff format --check .

# Run type checking
mypy app

# Run security scan
bandit -r app

# Or run all pre-commit hooks
pre-commit run --all-files
```

### Frontend
```bash
cd frontend

# Lint
npm run lint
npm run format:check

# Build
npm run build

# Security
npm audit
```

## Troubleshooting

### CI Failing
1. Check the "Checks" tab on your PR
2. Click on the failed job to see logs
3. Fix the issue locally
4. Push the fix
5. CI will automatically re-run

### Common Failures
- **Tests fail**: Code changes broke a test
- **Linting fail**: Run `ruff format .` to auto-fix
- **Type errors**: Add missing type annotations
- **Security**: Update vulnerable dependencies

## Coverage Reports

Coverage is tracked for every CI run:
- Backend: Currently 65.81%
- Frontend: Infrastructure ready, no tests yet

Reports are available as artifacts in the GitHub Actions run.
