"""Admin endpoints tests for audit events and event types."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_session_token, hash_token
from app.db.models.auth import LoginEvent, Session, User

pytestmark = [pytest.mark.admin, pytest.mark.integration]


async def _create_user(db, email: str, is_active: bool = True) -> User:
    now = datetime.now(UTC)
    user = User(email=email, is_active=is_active, created_at=now, updated_at=now)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _auth_cookies_for_user(db, user: User) -> dict[str, str]:
    token = create_session_token()
    token_hash = hash_token(token)
    now = datetime.now(UTC)
    sess = Session(
        user_id=user.id,
        token_hash=token_hash,
        created_at=now - timedelta(days=10),
        expires_at=now + timedelta(days=7),
        ip="127.0.0.1",
        user_agent="test",
    )
    db.add(sess)
    await db.commit()
    return {"ff_sess": token}


class TestAuditEventsAuthz:
    @pytest.mark.asyncio
    async def test_events_unauthenticated_returns_401(self, client: AsyncClient):
        r = await client.get("/api/v1/admin/audit/events")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_events_inactive_user_returns_403(
        self, client: AsyncClient, db_session
    ):
        user = await _create_user(db_session, "inactive@test.com", is_active=False)
        cookies = await _auth_cookies_for_user(db_session, user)
        r = await client.get("/api/v1/admin/audit/events", cookies=cookies)
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_events_active_user_returns_entries(
        self, client: AsyncClient, db_session
    ):
        active = await _create_user(db_session, "active@test.com", is_active=True)
        # Create events for active and another user
        other = await _create_user(db_session, "other@test.com", is_active=True)
        now = datetime.now(UTC)
        db_session.add_all(
            [
                LoginEvent(
                    user_id=active.id, event_type="magic_link_used", created_at=now
                ),
                LoginEvent(
                    user_id=other.id, event_type="webauthn_login", created_at=now
                ),
            ]
        )
        await db_session.commit()
        cookies = await _auth_cookies_for_user(db_session, active)
        r = await client.get("/api/v1/admin/audit/events", cookies=cookies)
        assert r.status_code == 200
        data = r.json()
        assert "entries" in data and isinstance(data["entries"], list)
        assert data["total"] >= 2


class TestAuditEventsFilteringAndValidation:
    @pytest.mark.asyncio
    async def test_filter_by_user_id_returns_only_user_events(
        self, client: AsyncClient, db_session
    ):
        u1 = await _create_user(db_session, "u1@test.com")
        u2 = await _create_user(db_session, "u2@test.com")
        now = datetime.now(UTC)
        db_session.add_all(
            [
                LoginEvent(user_id=u1.id, event_type="magic_link_used", created_at=now),
                LoginEvent(user_id=u2.id, event_type="magic_link_used", created_at=now),
            ]
        )
        await db_session.commit()
        cookies = await _auth_cookies_for_user(db_session, u1)
        r = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"user_id": str(u1.id)},
        )
        assert r.status_code == 200
        data = r.json()
        assert all(e["user_id"] == str(u1.id) for e in data["entries"])

    @pytest.mark.asyncio
    async def test_filter_by_event_type(self, client: AsyncClient, db_session):
        u = await _create_user(db_session, "evt@test.com")
        now = datetime.now(UTC)
        db_session.add_all(
            [
                LoginEvent(user_id=u.id, event_type="type_a", created_at=now),
                LoginEvent(user_id=u.id, event_type="type_b", created_at=now),
            ]
        )
        await db_session.commit()
        cookies = await _auth_cookies_for_user(db_session, u)
        r = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"event_type": "type_a"},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["entries"]) >= 1
        assert all(e["event_type"] == "type_a" for e in data["entries"])

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, client: AsyncClient, db_session):
        u = await _create_user(db_session, "date@test.com")
        t0 = datetime.now(UTC) - timedelta(days=3)
        t1 = datetime.now(UTC) - timedelta(days=2)
        t2 = datetime.now(UTC) - timedelta(days=1)
        db_session.add_all(
            [
                LoginEvent(user_id=u.id, event_type="type_a", created_at=t0),
                LoginEvent(user_id=u.id, event_type="type_a", created_at=t1),
                LoginEvent(user_id=u.id, event_type="type_a", created_at=t2),
            ]
        )
        await db_session.commit()
        cookies = await _auth_cookies_for_user(db_session, u)
        # start_date only
        r1 = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"start_date": t1.isoformat()},
        )
        assert r1.status_code == 200
        n1 = len(r1.json()["entries"])
        # end_date only
        r2 = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"end_date": t1.isoformat()},
        )
        assert r2.status_code == 200
        n2 = len(r2.json()["entries"])
        # both (range)
        r3 = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"start_date": t0.isoformat(), "end_date": t2.isoformat()},
        )
        assert r3.status_code == 200
        n3 = len(r3.json()["entries"])
        assert n1 <= 2 and n2 <= 2 and n3 >= 2

    @pytest.mark.asyncio
    async def test_invalid_user_id_format_returns_400(
        self, client: AsyncClient, db_session
    ):
        u = await _create_user(db_session, "badfmt@test.com")
        cookies = await _auth_cookies_for_user(db_session, u)
        r = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"user_id": "not-a-uuid"},
        )
        assert r.status_code == 400


class TestAuditEventsPaginationAndResponse:
    @pytest.mark.asyncio
    async def test_pagination_first_middle_last(self, client: AsyncClient, db_session):
        u = await _create_user(db_session, "page@test.com")
        now = datetime.now(UTC)
        # create 120 events to exercise multiple pages
        for _i in range(120):
            db_session.add(
                LoginEvent(user_id=u.id, event_type="type_a", created_at=now)
            )
        await db_session.commit()
        cookies = await _auth_cookies_for_user(db_session, u)
        # first page
        r1 = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"page": 1, "page_size": 50},
        )
        data1 = r1.json()
        assert (
            data1["page"] == 1
            and data1["page_size"] == 50
            and data1["has_more"] is True
        )
        # middle page
        r2 = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"page": 2, "page_size": 50},
        )
        data2 = r2.json()
        assert data2["page"] == 2 and data2["has_more"] is True
        # last page
        r3 = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"page": 3, "page_size": 50},
        )
        data3 = r3.json()
        assert data3["page"] == 3 and data3["has_more"] is False
        # beyond results
        r4 = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"page": 5, "page_size": 50},
        )
        data4 = r4.json()
        assert data4["entries"] == [] and data4["total"] == 120

    @pytest.mark.asyncio
    async def test_response_includes_user_email_and_nulls(
        self, client: AsyncClient, db_session
    ):
        u = await _create_user(db_session, "resp@test.com")
        now = datetime.now(UTC)
        # One event with user, one without
        db_session.add_all(
            [
                LoginEvent(user_id=u.id, event_type="type_a", created_at=now),
                LoginEvent(user_id=None, event_type="type_a", created_at=now),
            ]
        )
        await db_session.commit()
        cookies = await _auth_cookies_for_user(db_session, u)
        r = await client.get("/api/v1/admin/audit/events", cookies=cookies)
        data = r.json()
        # Should contain entries with user_email and entries with null user_id/email
        has_with_email = any(e["user_email"] == u.email for e in data["entries"])
        has_nulls = any(
            e["user_id"] is None and e["user_email"] is None for e in data["entries"]
        )
        assert has_with_email and has_nulls

    @pytest.mark.asyncio
    async def test_total_matches_filtered_results(
        self, client: AsyncClient, db_session
    ):
        u = await _create_user(db_session, "total@test.com")
        now = datetime.now(UTC)
        for _i in range(10):
            db_session.add(
                LoginEvent(user_id=u.id, event_type="type_a", created_at=now)
            )
        await db_session.commit()
        cookies = await _auth_cookies_for_user(db_session, u)
        r = await client.get(
            "/api/v1/admin/audit/events",
            cookies=cookies,
            params={"event_type": "type_a", "page_size": 5},
        )
        data = r.json()
        assert data["total"] >= 10


class TestEventTypesEndpoint:
    @pytest.mark.asyncio
    async def test_event_types_unauthenticated_401(self, client: AsyncClient):
        r = await client.get("/api/v1/admin/audit/event-types")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_event_types_inactive_user_403(self, client: AsyncClient, db_session):
        user = await _create_user(
            db_session, "inactive-types@test.com", is_active=False
        )
        cookies = await _auth_cookies_for_user(db_session, user)
        r = await client.get("/api/v1/admin/audit/event-types", cookies=cookies)
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_event_types_authenticated_returns_sorted_distinct(
        self, client: AsyncClient, db_session
    ):
        u = await _create_user(db_session, "types@test.com")
        now = datetime.now(UTC)
        db_session.add_all(
            [
                LoginEvent(user_id=u.id, event_type="b_event", created_at=now),
                LoginEvent(user_id=u.id, event_type="a_event", created_at=now),
                LoginEvent(user_id=u.id, event_type="a_event", created_at=now),
            ]
        )
        await db_session.commit()
        cookies = await _auth_cookies_for_user(db_session, u)
        r = await client.get("/api/v1/admin/audit/event-types", cookies=cookies)
        assert r.status_code == 200
        data = r.json()
        assert data["event_types"] == sorted(set(data["event_types"]))

    @pytest.mark.asyncio
    async def test_event_types_empty_returns_empty_list(
        self, client: AsyncClient, db_session
    ):
        u = await _create_user(db_session, "types-empty@test.com")
        cookies = await _auth_cookies_for_user(db_session, u)
        r = await client.get("/api/v1/admin/audit/event-types", cookies=cookies)
        assert r.status_code == 200
        assert r.json()["event_types"] == []
