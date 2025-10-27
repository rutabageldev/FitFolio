"""CSRF protection middleware using double-submit cookie pattern."""

import os
import secrets

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.logging import get_logger

log = get_logger()

CSRF_TOKEN_LENGTH = 32
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
CSRF_TOKEN_LIFETIME = 3600 * 24 * 14  # 14 days (matches session)

# Methods that require CSRF protection
PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

# Paths exempt from CSRF (e.g., initial login endpoints)
EXEMPT_PATHS = {
    "/auth/magic-link/start",  # Initial auth request, no session yet
    "/auth/magic-link/verify",  # Token-based, already protected
    "/_debug/",  # Debug endpoints
    "/healthz",  # Health check
}


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def should_check_csrf(request: Request) -> bool:
    """Determine if request requires CSRF validation."""
    if request.method not in PROTECTED_METHODS:
        return False

    # Check if path is exempt
    path = request.url.path
    for exempt in EXEMPT_PATHS:
        if path.startswith(exempt):
            return False

    return True


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection using double-submit cookie pattern.

    - Sets CSRF token in cookie (HttpOnly=false for JS access)
    - Validates token from X-CSRF-Token header matches cookie
    - Generates new token if missing or on GET requests
    """

    def __init__(self, app):
        super().__init__(app)
        self.cookie_secure = os.getenv("CSRF_COOKIE_SECURE", "false").lower() == "true"

    async def dispatch(self, request: Request, call_next):
        # Get CSRF token from cookie
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)

        # Check if this request needs CSRF validation
        needs_csrf = should_check_csrf(request)

        if needs_csrf:
            # Get token from header
            csrf_header = request.headers.get(CSRF_HEADER_NAME)

            if not csrf_cookie or not csrf_header:
                log.warning(
                    "csrf_validation_failed",
                    reason="missing_token",
                    path=request.url.path,
                    has_cookie=bool(csrf_cookie),
                    has_header=bool(csrf_header),
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "CSRF token missing. Please refresh and try again."
                    },
                )

            # Validate tokens match (constant-time comparison)
            if not secrets.compare_digest(csrf_cookie, csrf_header):
                log.warning(
                    "csrf_validation_failed",
                    reason="token_mismatch",
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "CSRF token invalid. Please refresh and try again."
                    },
                )

        # Process request
        response: Response = await call_next(request)

        # Set or refresh CSRF token in cookie
        # Generate new token if missing, or on safe methods (GET, HEAD, OPTIONS)
        if not csrf_cookie or request.method in {"GET", "HEAD", "OPTIONS"}:
            new_token = generate_csrf_token()
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=new_token,
                max_age=CSRF_TOKEN_LIFETIME,
                httponly=False,  # MUST be False so JS can read it
                secure=self.cookie_secure,  # True in production with HTTPS
                samesite="lax",
            )
            # Also set in response header for convenience
            response.headers[CSRF_HEADER_NAME] = new_token

        return response
