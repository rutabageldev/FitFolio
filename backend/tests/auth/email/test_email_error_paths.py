"""Email verification error-path tests."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestResendVerificationErrors:
    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_resend_verification_email_failure_returns_500_for_eligible_user(
        self, mock_send_email, client: AsyncClient, db_session
    ):
        """Eligible unverified user email send failure should return 500."""
        from datetime import UTC, datetime
        from smtplib import SMTPException

        from app.db.models.auth import User

        # Create eligible user (active, not verified)
        now = datetime.now(UTC)
        user = User(
            email="emailfail@test.com",
            is_active=True,
            is_email_verified=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()

        mock_send_email.side_effect = SMTPException("SMTP error")

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "emailfail@test.com"},
        )
        assert response.status_code == 500
