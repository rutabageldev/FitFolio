# Test Plan Index

**Purpose:** Track test coverage planning and implementation progress.

**Current Overall Coverage:** 65.88% (753/1143 lines)
**Target Overall Coverage:** 85%+

---

## Test Plans by Priority

### 🚨 CRITICAL Priority (Must reach 85%+)

| Module | Current | Target | Test Plan | Status |
|--------|---------|--------|-----------|--------|
| [auth.py](auth.md) | 41.03% | 85% | auth.md | ⏳ Planning Complete |
| [deps.py](deps.md) | 45.71% | 85% | deps.md | 🚧 12 tests implemented |

### 🔥 HIGH Priority (Should reach 85%+)

| Module | Current | Target | Test Plan | Status |
|--------|---------|--------|-----------|--------|
| [webauthn.py](webauthn.md) | 58.14% | 85% | webauthn.md | ⏳ Planning Complete |

### 📊 MEDIUM Priority (Need improvement to 85%+)

| Module | Current | Target | Test Plan | Status |
|--------|---------|--------|-----------|--------|
| [admin.py](admin.md) | 75.68% | 85% | admin.md | ⏳ Planning Complete |

### ✅ Already Meeting Target (≥85%)

| Module | Current | Notes |
|--------|---------|-------|
| email.py | 100.00% | ✅ Complete |
| session_rotation.py | 100.00% | ✅ Complete |
| csrf.py | 100.00% | ✅ Complete |
| request_id.py | 100.00% | ✅ Complete |
| otel.py | 100.00% | ✅ Complete |
| dev.py | 100.00% | ✅ Complete |
| health.py | 100.00% | ✅ Complete |
| base.py | 100.00% | ✅ Complete |
| auth.py (models) | 100.00% | ✅ Complete |
| security.py | 97.78% | ✅ Nearly complete |
| rate_limit.py | 95.00% | ✅ Nearly complete |
| logging.py | 88.24% | ✅ Acceptable |
| rate_limiter.py | 84.75% | ✅ Acceptable |

---

## Coverage Gap Summary

### By Priority (Lines Missing)

1. **auth.py (v1)**: 240 lines missing (🚨 CRITICAL - largest gap)
2. **deps.py**: 19 lines missing (🚨 CRITICAL - auth dependency)
3. **webauthn.py**: 18 lines missing (🔥 HIGH - security)
4. **admin.py**: 18 lines missing (📊 MEDIUM - audit logs)

### Total Lines to Cover

- **Critical Modules**: 259 lines
- **High Modules**: 18 lines
- **Medium Modules**: 18 lines
- **Total**: 295 lines to reach 85% overall coverage

---

## Test Plan Files

- [README.md](README.md) - Test plan structure and guidelines
- [deps.md](deps.md) - API dependency injection (session management)
- [admin.md](admin.md) - Admin audit log endpoints
- [webauthn.md](webauthn.md) - WebAuthn manager (passkey operations)
- [auth.md](auth.md) - Authentication endpoints (magic link, WebAuthn, sessions)

---

## Implementation Progress Tracking

### Completed Test Plans (4/4)
- ✅ deps.py - 12/27 test cases identified
- ✅ admin.py - 31 test cases identified
- ✅ webauthn.py - 35 test cases identified
- ✅ auth.py - 76 test cases identified

### Implemented Tests
- ✅ deps.py - 12 tests created (ready to run)
- ⏳ admin.py - 0 tests (pending)
- ⏳ webauthn.py - 0 tests (pending)
- ⏳ auth.py - Partially covered in existing test files

### Next Steps
1. **Run deps.py tests** - Verify 12 tests pass, check coverage improvement
2. **Implement auth.py tests** - Largest gap, 240 missing lines
3. **Implement webauthn.py tests** - Security-critical, error path focus
4. **Implement admin.py tests** - Audit endpoint coverage
5. **Add CI coverage threshold** - Enforce 85% in GitHub Actions

---

## Estimated Effort

| Task | Effort | Status |
|------|--------|--------|
| Test Planning | 2 hours | ✅ Complete |
| deps.py implementation | 30 minutes | 🚧 Tests written, needs verification |
| auth.py implementation | 4-5 hours | ⏳ Pending (76 test cases) |
| webauthn.py implementation | 2-3 hours | ⏳ Pending (35 test cases) |
| admin.py implementation | 2-3 hours | ⏳ Pending (31 test cases) |
| CI integration | 30 minutes | ⏳ Pending |
| **Total** | **11-14 hours** | **15% complete** |

---

## Coverage Enforcement

### CI Integration Plan
- Add `--cov-fail-under=85` to pytest command in `.github/workflows/ci.yml`
- Block PRs that drop coverage below 85%
- Generate coverage report as CI artifact
- Add coverage badge to README.md

### Per-Module Targets
- Critical modules (auth, security): ≥85%
- Core modules (middleware, utilities): ≥85%
- Integration tests: ≥80%
- Overall project: ≥85%

---

**Last Updated:** 2025-11-06
**Next Review:** After deps.py tests are verified
