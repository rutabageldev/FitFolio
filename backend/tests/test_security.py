"""Tests for core security functions (tokens, hashing, session validation)."""

import pytest

from app.core.security import (
    create_magic_link_token,
    create_session_token,
    hash_magic_link_token,
    hash_token,
    verify_token_hash,
)


class TestTokenGeneration:
    """Test secure token generation."""

    def test_session_token_is_unique(self):
        """Session tokens should be unique."""
        token1 = create_session_token()
        token2 = create_session_token()
        assert token1 != token2

    def test_session_token_is_url_safe(self):
        """Session tokens should be URL-safe."""
        token = create_session_token()
        assert isinstance(token, str)
        assert len(token) > 0
        # URL-safe base64 only contains: A-Z, a-z, 0-9, -, _
        assert all(c.isalnum() or c in "-_" for c in token)

    def test_magic_link_token_is_unique(self):
        """Magic link tokens should be unique."""
        token1 = create_magic_link_token()
        token2 = create_magic_link_token()
        assert token1 != token2

    def test_magic_link_token_is_url_safe(self):
        """Magic link tokens should be URL-safe."""
        token = create_magic_link_token()
        assert isinstance(token, str)
        assert len(token) > 0
        assert all(c.isalnum() or c in "-_" for c in token)


class TestTokenHashing:
    """Test token hashing and verification."""

    def test_hash_token_is_deterministic(self):
        """Same token should produce same hash."""
        token = "test_token_12345"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2

    def test_hash_token_produces_bytes(self):
        """Hash should be bytes."""
        token = "test_token_12345"
        token_hash = hash_token(token)
        assert isinstance(token_hash, bytes)
        assert len(token_hash) == 32  # SHA-256 produces 32 bytes

    def test_different_tokens_produce_different_hashes(self):
        """Different tokens should produce different hashes."""
        token1 = "test_token_1"
        token2 = "test_token_2"
        hash1 = hash_token(token1)
        hash2 = hash_token(token2)
        assert hash1 != hash2

    def test_verify_token_hash_success(self):
        """Correct token should verify against its hash."""
        token = "test_token_12345"
        token_hash = hash_token(token)
        assert verify_token_hash(token, token_hash) is True

    def test_verify_token_hash_failure(self):
        """Wrong token should not verify against hash."""
        token = "test_token_12345"
        wrong_token = "wrong_token_12345"
        token_hash = hash_token(token)
        assert verify_token_hash(wrong_token, token_hash) is False

    def test_magic_link_hash_is_deterministic(self):
        """Same magic link token should produce same hash."""
        token = "magic_test_token"
        hash1 = hash_magic_link_token(token)
        hash2 = hash_magic_link_token(token)
        assert hash1 == hash2

    def test_magic_link_hash_produces_bytes(self):
        """Magic link hash should be bytes."""
        token = "magic_test_token"
        token_hash = hash_magic_link_token(token)
        assert isinstance(token_hash, bytes)
        assert len(token_hash) == 32


class TestSessionValidation:
    """Test session validation logic."""

    @pytest.mark.asyncio
    async def test_expired_session_not_returned(self, client, db_session):
        """Expired sessions should not be returned by validation."""
        from datetime import UTC, datetime, timedelta

        from app.core.security import create_session_token, hash_token
        from app.db.models.auth import Session, User

        # Create user
        now = datetime.now(UTC)
        user = User(
            email="expired@test.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create expired session
        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
        )
        db_session.add(session)
        await db_session.commit()

        # Try to use expired session
        response = await client.get("/auth/me", cookies={"ff_sess": token})
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_revoked_session_not_returned(self, client, db_session):
        """Revoked sessions should not be returned by validation."""
        from datetime import UTC, datetime, timedelta

        from app.core.security import create_session_token, hash_token
        from app.db.models.auth import Session, User

        # Create user
        now = datetime.now(UTC)
        user = User(
            email="revoked@test.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create revoked session
        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            revoked_at=datetime.now(UTC),  # Revoked
        )
        db_session.add(session)
        await db_session.commit()

        # Try to use revoked session
        response = await client.get("/auth/me", cookies={"ff_sess": token})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rotated_session_not_returned(self, client, db_session):
        """Rotated sessions should not be returned by validation."""
        from datetime import UTC, datetime, timedelta

        from app.core.security import create_session_token, hash_token
        from app.db.models.auth import Session, User

        # Create user
        now = datetime.now(UTC)
        user = User(
            email="rotated@test.com",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create rotated session
        token = create_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            rotated_at=datetime.now(UTC),  # Rotated
        )
        db_session.add(session)
        await db_session.commit()

        # Try to use rotated session
        response = await client.get("/auth/me", cookies={"ff_sess": token})
        assert response.status_code == 401
