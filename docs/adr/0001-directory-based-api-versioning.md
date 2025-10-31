# ADR-0001: Directory-Based API Versioning

**Status:** Accepted
**Date:** 2025-10-29
**Deciders:** Development Team
**Tags:** architecture, api, backend, versioning

## Context

The FitFolio API needed a versioning strategy to support backward compatibility as features evolve. We needed to choose between several approaches:
- Path-based versioning (`/api/v1/...`)
- Header-based versioning (`Accept: application/vnd.fitfolio.v1+json`)
- Query parameter versioning (`/api/users?version=1`)

Our requirements:
- Support running multiple API versions simultaneously
- Clear separation between versions
- Easy to deprecate old versions during transitions
- Simple for frontend clients to use
- Production-ready and maintainable

## Decision

Use directory-based versioning with the structure `app/api/v1/` and URL prefix `/api/v1/`.

All API endpoints are namespaced under `/api/v1/`:
- `/api/v1/auth/*`
- `/api/v1/admin/*`
- Future: `/api/v2/*` when breaking changes needed

Non-versioned endpoints:
- `/healthz` - Health checks
- `/_debug/*` - Development-only debug endpoints
- `/docs`, `/redoc`, `/openapi.json` - API documentation

## Rationale

**Why directory-based over other approaches:**
- **Simplicity:** Clear and explicit in URLs, easy to understand
- **Multiple versions:** Can run v1 and v2 simultaneously during transitions
- **Routing:** FastAPI router includes make this clean to implement
- **Industry standard:** Used by GitHub, Stripe, Twilio, and other major APIs
- **Backward compatibility:** Old clients continue working during migrations

**Why prefix-based in URLs (not headers):**
- More explicit and discoverable
- Easier to debug (visible in logs and browser dev tools)
- Simpler for frontend developers
- Better caching behavior

**Trade-offs considered:**
- Header-based: More "RESTful" but less discoverable, harder to debug
- Query params: Awkward, not commonly used for versioning
- No versioning: Would force breaking changes on all clients

## Consequences

### Positive
- Clear migration path for breaking changes
- Can maintain v1 while developing v2
- Easy to test both versions in parallel
- Deprecated versions can be removed cleanly
- Frontend knows exactly which version they're using

### Negative
- URL paths are slightly longer (`/api/v1` prefix)
- Need to maintain duplicate code during transitions (temporary)
- Router configuration slightly more complex

### Neutral
- All new endpoints must include version prefix
- Documentation must be clear about versioned vs. unversioned endpoints

## Implementation

**Directory Structure:**
```
app/
  api/
    v1/
      __init__.py  # Router aggregator
      auth.py      # Auth endpoints
      admin.py     # Admin endpoints
```

**Router Configuration (main.py):**
```python
from app.api.v1 import router as v1_router
app.include_router(v1_router, prefix="/api/v1")
```

**Related Commits:**
- Initial implementation: `97e6864`
- Directory restructure: `b5ebbcb`

**Tests Updated:** All 93 tests (now 138) updated to use `/api/v1/` prefix

## References

- Related ADR: ADR-0002 (Traefik Integration) - routing considerations
- FastAPI Versioning Guide: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- API Versioning Best Practices: https://www.troyhunt.com/your-api-versioning-is-wrong-which-is/
- Stripe API Versioning: https://stripe.com/docs/api/versioning
