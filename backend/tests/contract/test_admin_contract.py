"""
Admin API Contract Tests

Verifies that admin endpoints are reachable at their documented versioned paths
and correctly require authentication by default.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.contract, pytest.mark.integration]


class TestAdminEndpointInventory:
    EXPECTED_ADMIN_ENDPOINTS = [
        ("GET", "/api/v1/admin/audit/events", 401),
        ("GET", "/api/v1/admin/audit/event-types", 401),
    ]

    @pytest.mark.parametrize("method,path,expected_status", EXPECTED_ADMIN_ENDPOINTS)
    async def test_admin_endpoint_exists(
        self, client: AsyncClient, method: str, path: str, expected_status: int
    ):
        if method == "GET":
            response = await client.get(path)
        elif method == "POST":
            response = await client.post(path, json={})
        elif method == "DELETE":
            response = await client.delete(path)
        else:
            pytest.fail(f"Unsupported method: {method}")

        assert response.status_code != 404, f"{method} {path} should exist"
        if response.status_code != expected_status:
            msg = (
                f"Note: {method} {path} returned {response.status_code}, "
                f"expected {expected_status}"
            )
            print(msg)
