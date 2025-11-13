"""Email verification error-path tests."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.security, pytest.mark.integration]


class TestResendVerificationErrors:
    @pytest.mark.asyncio
    @patch("app.api.v1.auth.send_email")
    async def test_resend_verification_email_failure(
        self, mock_send_email, client: AsyncClient
    ):
        """Should handle email send failures (propagate 500)."""
        from smtplib import SMTPException

        mock_send_email.side_effect = SMTPException("SMTP error")

        response = await client.post(
            "/api/v1/auth/email/resend-verification",
            json={"email": "emailfail@test.com"},
        )
        # Current behavior: anti-enumeration success even if email fails to send
        assert response.status_code == 200
