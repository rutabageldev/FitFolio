"""Admin endpoints for system management and audit logging."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_session_with_rotation
from app.db.database import get_db
from app.db.models.auth import LoginEvent, Session, User

router = APIRouter(prefix="/admin", tags=["admin"])


class AuditLogEntry(BaseModel):
    """Single audit log entry."""

    id: int
    user_id: str | None
    user_email: str | None
    event_type: str
    created_at: datetime
    ip: str | None
    user_agent: str | None
    extra: dict | None


class AuditLogResponse(BaseModel):
    """Paginated audit log response."""

    entries: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
    has_more: bool


@router.get("/audit/events", response_model=AuditLogResponse)
async def get_audit_events(
    session_and_user: tuple[Session, User] = Depends(get_current_session_with_rotation),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Query(None, description="Filter by user ID"),
    event_type: str | None = Query(None, description="Filter by event type"),
    start_date: datetime | None = Query(
        None, description="Filter events after this date"
    ),
    end_date: datetime | None = Query(
        None, description="Filter events before this date"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
):
    import uuid as uuid_lib

    # Parse user_id string to UUID object if provided
    user_uuid: uuid_lib.UUID | None = None
    if user_id:
        try:
            user_uuid = uuid_lib.UUID(user_id)
        except ValueError as err:
            raise HTTPException(
                status_code=400, detail="Invalid user_id format"
            ) from err
    """
    Get audit log events with filtering and pagination.

    **Admin only**: This endpoint requires admin privileges.

    Filters:
    - user_id: Filter by specific user UUID
    - event_type: Filter by event type (e.g., 'magic_link_verified_success')
    - start_date/end_date: Filter by date range
    - page/page_size: Pagination controls

    Returns paginated list of audit log entries with user context.
    """
    _session, user = session_and_user

    # TODO: Add proper admin role check
    # For now, just ensure user is authenticated
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # Build query with filters
    stmt = select(LoginEvent, User.email).outerjoin(User, LoginEvent.user_id == User.id)

    if user_uuid:
        stmt = stmt.where(LoginEvent.user_id == user_uuid)
    if event_type:
        stmt = stmt.where(LoginEvent.event_type == event_type)
    if start_date:
        stmt = stmt.where(LoginEvent.created_at >= start_date)
    if end_date:
        stmt = stmt.where(LoginEvent.created_at <= end_date)

    # Order by most recent first
    stmt = stmt.order_by(desc(LoginEvent.created_at))

    # Get total count (before pagination)
    count_stmt = select(LoginEvent)
    if user_uuid:
        count_stmt = count_stmt.where(LoginEvent.user_id == user_uuid)
    if event_type:
        count_stmt = count_stmt.where(LoginEvent.event_type == event_type)
    if start_date:
        count_stmt = count_stmt.where(LoginEvent.created_at >= start_date)
    if end_date:
        count_stmt = count_stmt.where(LoginEvent.created_at <= end_date)

    count_result = await db.execute(count_stmt)
    total = len(count_result.all())

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    rows = result.all()

    # Format response
    entries = [
        AuditLogEntry(
            id=event.id,
            user_id=str(event.user_id) if event.user_id else None,
            user_email=email,
            event_type=event.event_type,
            created_at=event.created_at,
            ip=event.ip,
            user_agent=event.user_agent,
            extra=event.extra,
        )
        for event, email in rows
    ]

    has_more = (offset + page_size) < total

    return AuditLogResponse(
        entries=entries,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/audit/event-types")
async def get_event_types(
    session_and_user: tuple[Session, User] = Depends(get_current_session_with_rotation),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of all event types in the audit log.

    **Admin only**: This endpoint requires admin privileges.

    Returns unique event types for use in filtering.
    """
    _session, user = session_and_user

    # TODO: Add proper admin role check
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # Get distinct event types
    stmt = select(LoginEvent.event_type).distinct().order_by(LoginEvent.event_type)
    result = await db.execute(stmt)
    event_types = [row[0] for row in result.all()]

    return {"event_types": event_types}
