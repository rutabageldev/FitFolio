"""
API Contract Tests

These tests verify that documented API endpoints are reachable at their expected
paths. This catches regressions when versioning or routing changes.
"""

import pytest
from httpx import AsyncClient

# This suite exercises the app boundary and should be treated as integration + contract
pytestmark = [pytest.mark.contract, pytest.mark.integration]


class TestHealthEndpoints:
    """Verify health check endpoints are accessible."""

    async def test_healthz_endpoint_exists(self, client: AsyncClient):
        """Health check should be at /healthz (not versioned)."""
        response = await client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_healthz_not_at_api_prefix(self, client: AsyncClient):
        """Health check should NOT be at /api/healthz."""
        response = await client.get("/api/healthz")
        assert response.status_code in (
            403,
            404,
        ), "Health check should not be under /api"

    async def test_healthz_not_versioned(self, client: AsyncClient):
        """Health check should NOT be versioned."""
        response = await client.get("/api/v1/healthz")
        assert response.status_code in (
            403,
            404,
        ), "Health check should not be versioned"


class TestAPIVersioning:
    """Reserved for cross-cutting versioning assertions (kept minimal here)."""

    async def test_api_root_exists_and_lists_versions(self, client: AsyncClient):
        response = await client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data and "v1" in data["versions"]


class TestDebugEndpoints:
    """Verify debug endpoints are accessible (dev only)."""

    async def test_debug_mail_endpoint_exists(self, client: AsyncClient):
        """Debug mail endpoint should be at /_debug/mail (not versioned)."""
        response = await client.post("/_debug/mail?to=test@example.com")
        # Should exist (may succeed or fail, but not 404)
        assert response.status_code != 404, "Debug endpoint should exist"

    async def test_debug_not_versioned(self, client: AsyncClient):
        """Debug endpoints should NOT be versioned."""
        response = await client.post("/api/v1/_debug/mail?to=test@example.com")
        assert response.status_code in (403, 404), "Debug should not be versioned"


class TestAPIDocumentation:
    """Verify OpenAPI docs are accessible."""

    async def test_openapi_json_exists(self, client: AsyncClient):
        """OpenAPI schema should be available at /openapi.json."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    async def test_docs_ui_exists(self, client: AsyncClient):
        """Swagger UI should be available at /docs."""
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()

    async def test_redoc_ui_exists(self, client: AsyncClient):
        """ReDoc UI should be available at /redoc."""
        response = await client.get("/redoc")
        assert response.status_code == 200
        assert "redoc" in response.text.lower()


class TestEndpointInventory:
    """Global endpoint inventory kept minimal here (health/debug/docs)."""

    EXPECTED_GLOBAL = [
        ("GET", "/healthz", 200),
        ("GET", "/docs", 200),
        ("GET", "/redoc", 200),
        ("GET", "/openapi.json", 200),
    ]

    @pytest.mark.parametrize("method,path,expected_status", EXPECTED_GLOBAL)
    async def test_global_endpoint_exists(
        self,
        client: AsyncClient,
        method: str,
        path: str,
        expected_status: int | None,
    ):
        if expected_status is None:
            pytest.skip(f"Endpoint {path} is environment-specific")
        if method == "GET":
            response = await client.get(path)
        elif method == "POST":
            response = await client.post(path, json={})
        elif method == "DELETE":
            response = await client.delete(path)
        else:
            pytest.fail(f"Unsupported method: {method}")
        assert response.status_code != 404


class TestOldPathsRemoved:
    """
    Verify old (pre-versioning) paths are no longer accessible.

    These tests ensure we don't accidentally serve endpoints at both
    old and new paths, which would cause confusion and security issues.
    """

    OLD_PATHS_SHOULD_404 = [
        ("POST", "/auth/magic-link/start"),
        ("POST", "/auth/magic-link/verify"),
        ("GET", "/auth/me"),
        ("GET", "/auth/sessions"),
        ("POST", "/auth/logout"),
        ("GET", "/admin/audit/events"),
    ]

    @pytest.mark.parametrize("method,path", OLD_PATHS_SHOULD_404)
    async def test_old_path_not_accessible(
        self, client: AsyncClient, method: str, path: str
    ):
        """
        Verify old (unversioned) paths return 404.

        If this test fails, an endpoint is accessible at both old and
        new paths, which could cause:
        - Version confusion
        - Security bypasses (if old path has weaker security)
        - API documentation ambiguity
        """
        if method == "GET":
            response = await client.get(path)
        elif method == "POST":
            response = await client.post(path, json={})
        else:
            pytest.fail(f"Unsupported method: {method}")

        assert response.status_code in (403, 404), (
            f"{method} {path} should return 404 (endpoint moved to /api/v1). "
            f"Got {response.status_code} instead. "
            f"This could indicate the endpoint is accessible at both old and new paths."
        )


class TestFrontendProxyConfiguration:
    """
    Tests to verify frontend proxy configuration matches backend routes.

    These tests document what paths the frontend expects to be able to call,
    which helps coordinate changes between frontend and backend.
    """

    # Paths that frontend should be able to call
    FRONTEND_CALLABLE_PATHS = [
        "/healthz",  # Used by App.jsx ping button
        "/api/v1/auth/magic-link/start",  # Auth flows
        "/api/v1/auth/magic-link/verify",
        "/api/v1/auth/me",
        "/_debug/mail",  # Dev tools
    ]

    @pytest.mark.parametrize("path", FRONTEND_CALLABLE_PATHS)
    async def test_frontend_path_reachable(self, client: AsyncClient, path: str):
        """
        Verify paths used by frontend are reachable.

        If this test fails, either:
        1. Backend route was moved/removed (update frontend)
        2. Frontend is calling wrong path (update frontend)
        3. Proxy configuration is wrong (update vite.config.js)
        """
        # Try GET first (works for health, will 405 for POST-only)
        response = await client.get(path)

        # Accept any status except 404
        assert response.status_code != 404, (
            f"Frontend expects to call {path} but got 404. "
            f"Check if route was moved or removed. "
            f"Frontend code may need updating."
        )


class TestMakefileCommands:
    """
    Tests to verify Makefile helper commands use correct paths.

    These tests catch issues like the magic-link command using /auth
    instead of /api/v1/auth.
    """

    async def test_makefile_magic_link_path(self, client: AsyncClient):
        """
        Verify magic link endpoint used by Makefile is correct.

        The Makefile's `make magic-link` command should call the
        versioned endpoint at /api/v1/auth/magic-link/start.
        """
        # Test the current path in Makefile
        response = await client.post(
            "/api/v1/auth/magic-link/start",
            json={"email": "test@example.com"},
        )

        assert response.status_code != 404, (
            "make magic-link uses /api/v1/auth/magic-link/start which returned 404. "
            "Makefile may need updating if endpoint was moved."
        )

    async def test_makefile_health_check_path(self, client: AsyncClient):
        """Verify health check used by Makefile is correct."""
        # Used by `make be-health` command
        response = await client.get("/healthz")

        assert response.status_code == 200, (
            "make be-health expects /healthz to return 200. "
            "Health check endpoint may have moved."
        )
