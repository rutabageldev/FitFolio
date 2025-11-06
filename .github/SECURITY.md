# Security Policy

## Overview

FitFolio takes security seriously. This document outlines our security practices and how to report vulnerabilities.

## Security Features

### 1. Automated Security Scanning

Our CI/CD pipeline includes multiple security layers:

#### CodeQL Analysis
- **What**: Advanced semantic code analysis
- **When**: Every push and pull request
- **Coverage**: Python backend and TypeScript/JavaScript frontend
- **Detects**: SQL injection, XSS, command injection, hardcoded secrets, and more
- **Configuration**: Uses `security-extended` and `security-and-quality` query suites

#### Dependency Scanning
- **Backend (Python)**:
  - `pip-audit`: Scans for known CVEs in Python dependencies
  - Runs on every commit
- **Frontend (JavaScript/TypeScript)**:
  - `npm audit`: Checks for vulnerabilities in npm packages
  - Fails on moderate+ severity issues
- **Dependency Review**:
  - Reviews new dependencies added in pull requests
  - Blocks packages with moderate+ vulnerabilities
  - Rejects GPL-3.0 and AGPL-3.0 licensed dependencies

#### Static Analysis
- **Bandit**: Python security linter checking for common security issues
  - Hardcoded passwords and tokens
  - SQL injection vulnerabilities
  - Insecure crypto usage
  - And more...

### 2. Commit Signature Verification

- **Status**: Warning only (not enforced)
- **Purpose**: Verifies commit authenticity via GPG/SSH signatures
- **How to sign commits**: [GitHub Docs](https://docs.github.com/en/authentication/managing-commit-signature-verification)

### 3. Least Privilege Permissions

Our GitHub Actions workflows use minimal permissions:
```yaml
permissions:
  contents: read           # Read code only
  security-events: write   # Upload security findings
  pull-requests: read      # Review PR dependencies
```

### 4. Test Isolation

- All tests run in isolated Docker containers
- Test credentials are clearly marked and never used in production
- Services (PostgreSQL, Redis, MailHog) are ephemeral and destroyed after tests

## Reporting Vulnerabilities

### Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| other   | :x:                |

### Reporting Process

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **Preferred**: GitHub Security Advisories
   - Go to https://github.com/rutabageldev/FitFolio/security/advisories
   - Click "Report a vulnerability"

2. **Email**: [Your security contact email]

### What to Include

Please include:
- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact assessment

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Target**: Within 30 days for high/critical issues

## Security Best Practices for Contributors

### Code Review Checklist

- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all user inputs
- [ ] Parameterized queries (no string concatenation in SQL)
- [ ] Proper authentication and authorization checks
- [ ] HTTPS/TLS for all external communications
- [ ] Secure random number generation (`secrets` module, not `random`)
- [ ] No eval() or exec() on user input
- [ ] File upload restrictions and validation
- [ ] Rate limiting on sensitive endpoints

### Dependencies

- Always use exact versions in `requirements.txt` and `package-lock.json`
- Review dependency changes in pull requests
- Keep dependencies up to date
- Avoid dependencies with poor security track records

### Authentication

- Use WebAuthn (passkeys) as primary authentication
- JWT tokens with short expiration times
- Secure session management via Redis
- HTTP-only cookies for session tokens

### Data Protection

- All passwords hashed with bcrypt
- Sensitive data encrypted at rest
- PII handled according to GDPR/privacy regulations
- Database credentials via environment variables only

## Security Headers

The application implements security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy`

## Known Security Considerations

### Development Environment

- Default development credentials are intentionally weak for convenience
- `.env` files must never be committed to version control
- Use `.env.example` as a template with safe defaults

### Production Deployment

Before deploying to production:
- [ ] Change all default credentials
- [ ] Use strong, randomly generated secrets
- [ ] Enable SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Enable audit logging
- [ ] Review CORS settings
- [ ] Configure rate limiting

## License Compliance

Our dependency review blocks:
- **GPL-3.0**: Copyleft license with viral implications
- **AGPL-3.0**: More restrictive copyleft license

Acceptable licenses include:
- MIT, BSD, Apache-2.0, ISC
- LGPL (with proper dynamic linking)

## Security Updates

Security updates are announced via:
- GitHub Security Advisories
- Release notes with `[SECURITY]` tag
- This SECURITY.md file (changelog at bottom)

---

## Changelog

| Date | Change | Impact |
|------|--------|--------|
| 2025-11-06 | Added CodeQL analysis | Enhanced SAST coverage |
| 2025-11-06 | Added dependency review | PR-level vulnerability blocking |
| 2025-11-06 | Added commit verification | Authenticity checking |
| 2025-11-05 | Initial security policy | Established baseline |
