# ADR-0003: Passwordless Authentication Strategy

**Status:** Accepted
**Date:** 2025-10-26
**Deciders:** Development Team
**Tags:** security, authentication, backend, ux

## Context

FitFolio needed an authentication system that prioritizes both security and user experience. Traditional password-based authentication has well-known problems:
- Password reuse across sites
- Weak passwords
- Phishing attacks
- Password reset flows
- Storage and hashing complexity
- Credential stuffing attacks

**Requirements:**
- Strong security posture
- Excellent user experience
- Modern authentication standards
- No password management burden for users
- Support for multiple devices

## Decision

Implement passwordless authentication with two methods:
1. **Magic Links** - Primary authentication method
2. **WebAuthn (Passkeys)** - Enhanced security option

**No traditional passwords.** Users authenticate via email (magic link) or biometrics/security keys (WebAuthn).

## Rationale

**Why Passwordless:**
- **Security:** Eliminates password-related vulnerabilities
- **UX:** No passwords to remember, type, or reset
- **Modern:** Aligns with industry trends (Apple Passkeys, Google Passwordless)
- **Phishing-resistant:** WebAuthn uses public key cryptography
- **Simpler codebase:** No password hashing, reset flows, complexity requirements

**Why Magic Links as Primary:**
- **Universal:** Works on all devices with email
- **Familiar:** Users understand "click link in email"
- **Low friction:** No additional setup required
- **Passwordless gateway:** Easy entry point for all users

**Why WebAuthn as Enhanced Option:**
- **Strongest security:** Phishing-resistant, hardware-backed
- **Best UX (when available):** Biometric authentication
- **Future-proof:** Industry standard (FIDO2/WebAuthn)
- **Multi-device:** Users can register multiple authenticators

**Trade-offs:**
- Depends on email delivery (mitigated: reliable SMTP, Mailpit for dev)
- WebAuthn not available on all devices (mitigated: magic link fallback)
- No offline authentication (acceptable for fitness tracking app)

## Consequences

### Positive
- No password database to protect or breach
- No password reset flows needed
- Phishing-resistant authentication (WebAuthn)
- Better user experience (no passwords to manage)
- Simpler security model
- Modern, forward-looking architecture

### Negative
- Depends on email delivery reliability
- Users must have email access to authenticate
- WebAuthn requires device support (not all browsers/devices)
- Less familiar to some users (education needed)

### Neutral
- Sessions still needed (not stateless like JWT)
- Email becomes the account recovery mechanism

## Implementation

**Authentication Flow:**

**Magic Link:**
1. User enters email
2. Backend generates secure token, sends email
3. User clicks link with token
4. Backend validates token, creates session
5. Session cookie returned to client

**WebAuthn:**
1. User registers authenticator (after magic link login)
2. Server generates challenge, client signs with authenticator
3. Public key stored server-side
4. Future logins: challenge-response with authenticator
5. Session created on successful authentication

**Security Measures:**
- SHA-256 token hashing
- 15-minute magic link expiry
- One-time use tokens
- Account lockout after failed attempts
- Email verification required
- Session rotation
- CSRF protection
- Rate limiting

**Database Schema:**
- `users` - No password field
- `magic_link_tokens` - Hashed tokens with expiry
- `webauthn_credentials` - Public keys and metadata
- `sessions` - Opaque server-side sessions

**Related Commits:**
- Initial implementation: Phase 1 (2025-10-26)
- Email verification: `1aa5984`
- Account lockout: `e0f5b18`

## References

- Related ADR: ADR-0004 (Server-Side Sessions)
- WebAuthn Specification: https://www.w3.org/TR/webauthn-2/
- FIDO Alliance: https://fidoalliance.org/
- Magic Link Best Practices: https://postmarkapp.com/guides/magic-links
- py_webauthn library: https://github.com/duo-labs/py_webauthn
