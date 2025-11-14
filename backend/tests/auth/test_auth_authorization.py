"""Authorization tests for auth endpoints.

Tests unauthenticated access and inactive user handling across all endpoints.
"""

from datetime import UTC, datetime

import pytest
import pytest_asyncio

from app.db.models.auth import User


@pytest_asyncio.fixture
async def inactive_user(db_session):
    """Create an inactive user for testing."""
    now = datetime.now(UTC)
    user = User(
        email="inactive@test.com",
        is_active=False,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestWebAuthnRegistrationAuthorization:
    """Test authorization for WebAuthn registration endpoints."""

    pass  # TODO: Implement authorization tests


class TestWebAuthnAuthenticationAuthorization:
    """Test authorization for WebAuthn authentication endpoints."""

    pass  # TODO: Implement authorization tests


class TestCredentialManagementAuthorization:
    """Test authorization for credential management endpoints."""

    pass  # TODO: Implement authorization tests


class TestSessionManagementAuthorization:
    """Test authorization for session management endpoints."""

    pass  # TODO: Implement authorization tests


class TestUserEndpointAuthorization:
    """Test authorization for user endpoints."""

    @pytest.mark.asyncio
    async def test_me_endpoint_unauthenticated(self):
        pass  # TODO: Implement test


class TestMagicLinkAuthorization:
    pass  # TODO: Implement authorization tests


class TestEmailVerificationAuthorization:
    """Test authorization for email verification endpoints."""

    pass  # TODO: Implement authorization tests
