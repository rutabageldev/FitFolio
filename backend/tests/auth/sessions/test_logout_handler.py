from datetime import UTC, datetime, timedelta

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from starlette.responses import Response

from app.api.v1.auth import logout
from app.core.security import create_session_token, hash_token
from app.db.models.auth import Session, User

pytestmark = [pytest.mark.security, pytest.mark.integration]


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookie(db_session):
    now = datetime.now(UTC)
    user = User(
        email="logout@test.com",
        is_active=True,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create a valid, unrevoked session
    raw = create_session_token()
    sess = Session(
        user_id=user.id,
        token_hash=hash_token(raw),
        created_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=10),
    )
    db_session.add(sess)
    await db_session.commit()
    await db_session.refresh(sess)

    # Call handler
    resp = Response()
    token = HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw)
    await logout(response=resp, db=db_session, token=token)

    # Cookie cleared
    set_cookie = resp.headers.get("set-cookie", "")
    assert "ff_sess=" in set_cookie

    # Session revoked
    await db_session.refresh(sess)
    assert sess.revoked_at is not None

    # Ensure only one session exists and is revoked
    rows = (await db_session.execute(select(Session))).scalars().all()
    assert len(rows) == 1 and rows[0].revoked_at is not None
