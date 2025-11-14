### Domain: Deps (dependency injection)

Areas

- Request dependencies (`Depends(...)`) for session retrieval/rotation
- Cookie handling and environment flags (e.g., `COOKIE_SECURE`)

Tests

- Validate cookie attributes (HttpOnly, SameSite, Secure when configured)
- Ensure rotation rules apply equally to optional and required dependencies
