"""Authorization tests for session-related endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestSessionManagementAuthorization:
    """Test authorization for session management endpoints."""

    @pytest.mark.asyncio
    async def test_list_sessions_unauthenticated(self, client: AsyncClient, csrf_token):
        """Should reject unauthenticated request."""
        response = await client.get(
            "/api/v1/auth/sessions",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 401


class TestUserEndpointAuthorization:
    """Authorization for user-facing session endpoints."""

    @pytest.mark.asyncio
    async def test_me_endpoint_unauthenticated(self, client: AsyncClient, csrf_token):
        """Should reject unauthenticated request to /me."""
        response = await client.get(
            "/api/v1/auth/me",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_revoke_session_unauthenticated(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject unauthenticated request."""
        import uuid

        session_id = str(uuid.uuid4())
        response = await client.delete(
            f"/api/v1/auth/sessions/{session_id}",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_revoke_all_other_sessions_unauthenticated(
        self, client: AsyncClient, csrf_token
    ):
        """Should reject unauthenticated request."""
        response = await client.post(
            "/api/v1/auth/sessions/revoke-all-others",
            cookies={"csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 401
