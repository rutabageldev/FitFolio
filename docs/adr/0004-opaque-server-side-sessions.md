# ADR-0004: Opaque Server-Side Sessions over JWT

**Status:** Accepted
**Date:** 2025-10-26
**Deciders:** Development Team
**Tags:** security, authentication, backend, sessions

## Context

After deciding on passwordless authentication (ADR-0003), we needed to choose a session management strategy. The two primary approaches are:

1. **JWT (JSON Web Tokens)** - Stateless, client-side storage
2. **Server-side sessions** - Stateful, opaque session tokens

**Requirements:**
- Secure session management
- Ability to revoke sessions
- Session rotation capability
- Audit trail
- Protect against token theft

## Decision

Use **opaque server-side sessions** with the following characteristics:
- Sessions stored in PostgreSQL database
- Opaque session tokens (random, reveal nothing)
- HttpOnly, Secure, SameSite=Lax cookies
- 30-day session expiry (7-day rotation threshold)
- SHA-256 token hashing in database

**No JWTs for session management.**

## Rationale

**Why Server-Side Sessions:**
- **Instant revocation:** Can immediately invalidate sessions
- **Session management:** Users can view and revoke active sessions
- **Rotation:** Can rotate session tokens for enhanced security
- **Audit trail:** Full history of session activity in database
- **Shorter tokens:** Opaque tokens are shorter than JWTs
- **Secrets safe:** No secrets embedded in tokens

**Why Not JWT:**
- **Cannot revoke:** JWTs valid until expiry (without complex infrastructure)
- **No rotation:** Rotating JWTs requires additional state anyway
- **Token size:** JWTs larger than opaque tokens
- **Secret exposure risk:** Signing secrets in application, if leaked all tokens compromised
- **Complexity:** Need to handle expiry, refresh tokens, etc.
- **Stateless myth:** Most JWT implementations add state anyway (blacklists, etc.)

**Security Considerations:**
- Tokens hashed with SHA-256 before storage (protect against DB compromise)
- HttpOnly cookies (JavaScript cannot access)
- Secure flag (HTTPS only)
- SameSite=Lax (CSRF protection)
- Session rotation (7-day threshold)
- IP address and User-Agent tracking

**Trade-offs:**
- Database lookup on every request (acceptable, PostgreSQL is fast)
- Slightly more complex than JWT (worth it for security)
- Harder to use with microservices (not a concern for monolith)

## Consequences

### Positive
- Sessions can be revoked instantly (security, user control)
- Full audit trail of authentication activity
- Session rotation for enhanced security
- User-facing session management features
- Shorter, opaque tokens
- No JWT complexity (refresh tokens, etc.)

### Negative
- Database query on every authenticated request
- Server-side state (not "stateless")
- Harder to scale horizontally (mitigated: PostgreSQL handles this fine)

### Neutral
- Session table grows over time (mitigated: cleanup job)
- Need to handle session expiry and cleanup

## Implementation

**Database Schema:**
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    token_hash BYTEA NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    rotated_at TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);
```

**Session Creation:**
```python
def create_session(user_id: UUID) -> str:
    token = secrets.token_urlsafe(32)  # 256 bits
    token_hash = hashlib.sha256(token.encode()).digest()
    expires_at = datetime.utcnow() + timedelta(days=30)
    # Store in database with token_hash
    return token  # Return plain token to client
```

**Cookie Configuration:**
```python
response.set_cookie(
    "session_token",
    value=session_token,
    httponly=True,
    secure=True,  # HTTPS only
    samesite="lax",
    max_age=30 * 24 * 60 * 60,  # 30 days
)
```

**Session Features:**
- List active sessions: `GET /api/v1/auth/sessions`
- Revoke session: `DELETE /api/v1/auth/sessions/{id}`
- Revoke all others: `POST /api/v1/auth/sessions/revoke-all-others`
- Automatic rotation (7-day threshold)
- Automatic cleanup (expired + 90-day-old rotated)

**Related Commits:**
- Initial sessions: Phase 1 (2025-10-26)
- Session rotation: `4f879ea`
- Session management: `fccb223`

## References

- Related ADR: ADR-0003 (Passwordless Authentication)
- OWASP Session Management: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- JWT vs Sessions: https://float-middle.com/json-web-tokens-jwt-vs-sessions/
- Stop Using JWT for Sessions: http://cryto.net/~joepie91/blog/2016/06/13/stop-using-jwt-for-sessions/
