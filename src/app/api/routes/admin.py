"""Admin API endpoints — user management, scroll CRUD, payment list, settings, audit, commission payout."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_user, require_role
from app.bot.services.commission import get_commission_balance, process_payout
from app.shared.database import session_factory
from app.shared.models.audit import AuditLog
from app.shared.models.commission import CommissionBalance
from app.shared.models.completion import UserCompletion
from app.shared.models.payment import Payment
from app.shared.models.scroll import Scroll
from app.shared.models.settings import Setting
from app.shared.models.user import Referral, User

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


# --- Pydantic response models for user management ---


class UserListItem(BaseModel):
    """Single user row in the admin list."""

    id: UUID
    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    archetype: Optional[str] = None
    xp: int
    streak: int
    is_active: bool
    paid_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    created_at: datetime


class UserListResponse(BaseModel):
    """Paginated user list response."""

    users: list[UserListItem]
    total: int
    page: int
    page_size: int


class UserPaymentItem(BaseModel):
    """Payment summary for user detail view."""

    id: UUID
    amount: int
    status: str
    created_at: datetime


class UserDetailResponse(BaseModel):
    """Full user profile with stats."""

    id: UUID
    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    archetype: Optional[str] = None
    xp: int
    streak: int
    is_active: bool
    paid_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    created_at: datetime
    timezone: str
    completions_count: int
    payments: list[UserPaymentItem]
    referrals_count: int
    commission_balance: Optional[dict] = None


class PayoutRequest(BaseModel):
    """Request body for manual commission payout."""

    user_id: UUID
    amount: int = Field(ge=1, description="Payout amount in kopecks")


# --- Scroll management Pydantic models ---


VALID_ARCHETYPES = ["head", "shell", "whirlwind", "ghost"]


class ScrollCreateRequest(BaseModel):
    """Request body for creating a scroll."""

    day_number: int = Field(ge=1, le=90, description="Day number 1-90")
    common_task: str = Field(min_length=1, description="Common (physical) task")
    ritual: str = Field(min_length=1, description="Morning ritual")
    habits: str = Field(min_length=1, description="Simple habits")
    micromovements: str = Field(min_length=1, description="Micro-movements")
    media_file_id: Optional[str] = None
    published_at: Optional[datetime] = None


class ScrollUpdateRequest(BaseModel):
    """Request body for updating a scroll (day_number immutable)."""

    common_task: str = Field(min_length=1, description="Common (physical) task")
    ritual: str = Field(min_length=1, description="Morning ritual")
    habits: str = Field(min_length=1, description="Simple habits")
    micromovements: str = Field(min_length=1, description="Micro-movements")
    media_file_id: Optional[str] = None
    published_at: Optional[datetime] = None


class ScrollResponse(BaseModel):
    """Single scroll in list or detail response."""

    id: UUID
    day_number: int
    common_task: str
    ritual: str
    habits: str
    micromovements: str
    media_file_id: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ScrollListResponse(BaseModel):
    """Paginated scroll list response."""

    scrolls: list[ScrollResponse]
    total: int
    page: int
    page_size: int


class PaymentResponse(BaseModel):
    """Payment with user info for admin list."""

    id: UUID
    user_id: UUID
    user_name: str
    user_username: Optional[str] = None
    amount: int
    currency: str
    status: str
    payment_method: Optional[str] = None
    platega_transaction_id: Optional[str] = None
    created_at: datetime


class PaymentListResponse(BaseModel):
    """Paginated payment list response."""

    payments: list[PaymentResponse]
    total: int
    page: int
    page_size: int


# --- Settings management Pydantic models ---


class SettingItem(BaseModel):
    """Single setting key-value pair."""

    key: str
    value: str


class SettingUpdateRequest(BaseModel):
    """Request body for bulk settings update."""

    settings: list[SettingItem]


class SettingResponse(BaseModel):
    """Setting with timestamps."""

    key: str
    value: str
    created_at: datetime
    updated_at: datetime


class SettingListResponse(BaseModel):
    """List of all settings."""

    settings: list[SettingResponse]


# --- Audit log Pydantic models ---


class AuditEntryResponse(BaseModel):
    """Single audit log entry."""

    id: UUID
    admin_id: Optional[UUID] = None
    admin_name: Optional[str] = None
    action: str
    details: Optional[str] = None
    created_at: datetime


class AuditListResponse(BaseModel):
    """Paginated audit log response."""

    entries: list[AuditEntryResponse]
    total: int
    page: int
    page_size: int


# --- Scroll management endpoints ---


@admin_router.get(
    "/scrolls",
    response_model=ScrollListResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def list_scrolls(
    day_number: Optional[int] = Query(None, ge=1, le=90, description="Filter by day number"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ScrollListResponse:
    """Return a paginated list of scrolls with optional filters."""
    async with session_factory() as session:
        query = select(Scroll)
        count_query = select(func.count(Scroll.id))

        if day_number is not None:
            query = query.where(Scroll.day_number == day_number)
            count_query = count_query.where(Scroll.day_number == day_number)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Scroll.day_number.asc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        scrolls = result.scalars().all()

        return ScrollListResponse(
            scrolls=[ScrollResponse.model_validate(s) for s in scrolls],
            total=total,
            page=page,
            page_size=page_size,
        )


@admin_router.get(
    "/scrolls/{scroll_id}",
    response_model=ScrollResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def get_scroll(scroll_id: UUID) -> ScrollResponse:
    """Return a single scroll by ID."""
    async with session_factory() as session:
        result = await session.execute(select(Scroll).where(Scroll.id == scroll_id))
        scroll = result.scalar_one_or_none()
        if scroll is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scroll not found",
            )
        return ScrollResponse.model_validate(scroll)


@admin_router.post(
    "/scrolls",
    response_model=ScrollResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def create_scroll(request: ScrollCreateRequest) -> ScrollResponse:
    """Create a new scroll. Enforces unique (day_number)."""
    async with session_factory() as session:
        scroll = Scroll(
            day_number=request.day_number,
            common_task=request.common_task,
            ritual=request.ritual,
            habits=request.habits,
            micromovements=request.micromovements,
            media_file_id=request.media_file_id,
            published_at=request.published_at,
        )
        session.add(scroll)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Scroll for day {request.day_number} already exists",
            )

        # Audit log
        audit_entry = AuditLog(
            action="scroll_created",
            details=f"day={request.day_number}",
        )
        session.add(audit_entry)
        await session.commit()

        await session.refresh(scroll)
        return ScrollResponse.model_validate(scroll)


@admin_router.put(
    "/scrolls/{scroll_id}",
    response_model=ScrollResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def update_scroll(
    scroll_id: UUID, request: ScrollUpdateRequest
) -> ScrollResponse:
    """Update scroll sections and media (day_number immutable)."""
    async with session_factory() as session:
        result = await session.execute(select(Scroll).where(Scroll.id == scroll_id))
        scroll = result.scalar_one_or_none()
        if scroll is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scroll not found",
            )

        scroll.common_task = request.common_task
        scroll.ritual = request.ritual
        scroll.habits = request.habits
        scroll.micromovements = request.micromovements
        scroll.media_file_id = request.media_file_id
        scroll.published_at = request.published_at

        audit_entry = AuditLog(
            action="scroll_updated",
            details=f"Updated scroll {scroll_id}",
        )
        session.add(audit_entry)
        await session.commit()
        await session.refresh(scroll)
        return ScrollResponse.model_validate(scroll)


@admin_router.delete(
    "/scrolls/{scroll_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def delete_scroll(scroll_id: UUID) -> None:
    """Delete a scroll and create an audit log entry."""
    async with session_factory() as session:
        result = await session.execute(select(Scroll).where(Scroll.id == scroll_id))
        scroll = result.scalar_one_or_none()
        if scroll is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scroll not found",
            )

        await session.delete(scroll)

        audit_entry = AuditLog(
            action="scroll_deleted",
            details=f"Deleted scroll {scroll_id}",
        )
        session.add(audit_entry)
        await session.commit()


# --- Payment management endpoints ---


@admin_router.get(
    "/payments",
    response_model=PaymentListResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def list_payments(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by payment status"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaymentListResponse:
    """Return a paginated list of payments with optional filters, joined with user info."""
    async with session_factory() as session:
        query = select(Payment, User).join(User, Payment.user_id == User.id)
        count_query = select(func.count(Payment.id))

        if status_filter:
            query = query.where(Payment.status == status_filter)
            count_query = count_query.where(Payment.status == status_filter)

        if user_id:
            query = query.where(Payment.user_id == user_id)
            count_query = count_query.where(Payment.user_id == user_id)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Payment.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        rows = result.all()

        payments = []
        for payment, user in rows:
            user_name = user.first_name
            if user.last_name:
                user_name += f" {user.last_name}"
            payments.append(
                PaymentResponse(
                    id=payment.id,
                    user_id=payment.user_id,
                    user_name=user_name,
                    user_username=user.username,
                    amount=payment.amount,
                    currency=payment.currency,
                    status=payment.status,
                    payment_method=payment.payment_method,
                    platega_transaction_id=payment.platega_transaction_id,
                    created_at=payment.created_at,
                )
            )

        return PaymentListResponse(
            payments=payments,
            total=total,
            page=page,
            page_size=page_size,
        )


@admin_router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def get_payment(payment_id: UUID) -> PaymentResponse:
    """Return a single payment with user info."""
    async with session_factory() as session:
        result = await session.execute(
            select(Payment, User)
            .join(User, Payment.user_id == User.id)
            .where(Payment.id == payment_id)
        )
        row = result.one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        payment, user = row
        user_name = user.first_name
        if user.last_name:
            user_name += f" {user.last_name}"

        return PaymentResponse(
            id=payment.id,
            user_id=payment.user_id,
            user_name=user_name,
            user_username=user.username,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            payment_method=payment.payment_method,
            platega_transaction_id=payment.platega_transaction_id,
            created_at=payment.created_at,
        )


# --- User management endpoints ---


@admin_router.get(
    "/users",
    response_model=UserListResponse,
    dependencies=[Depends(require_role("master", "leader", "curator"))],
)
async def list_users(
    search: str = Query("", description="Search by name, username, or telegram_id"),
    archetype: Optional[str] = Query(None, description="Filter by archetype"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    has_paid: Optional[bool] = Query(None, description="Filter by payment status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> UserListResponse:
    """Return a paginated list of users with optional search and filters."""
    async with session_factory() as session:
        query = select(User)
        count_query = select(func.count(User.id))

        # Search filter
        if search:
            search_term = f"%{search}%"
            # Try telegram_id exact match first
            telegram_id_filter = None
            try:
                tid = int(search)
                telegram_id_filter = User.telegram_id == tid
            except ValueError:
                pass

            name_filters = [
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.username.ilike(search_term),
            ]
            if telegram_id_filter is not None:
                name_filters.append(telegram_id_filter)
            where_clause = or_(*name_filters)
            query = query.where(where_clause)
            count_query = count_query.where(where_clause)

        # Archetype filter
        if archetype:
            query = query.where(User.archetype == archetype)
            count_query = count_query.where(User.archetype == archetype)

        # Active status filter
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        # Payment status filter
        if has_paid is not None:
            if has_paid:
                query = query.where(User.paid_at.isnot(None))
                count_query = count_query.where(User.paid_at.isnot(None))
            else:
                query = query.where(User.paid_at.is_(None))
                count_query = count_query.where(User.paid_at.is_(None))

        # Total count
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Paginated results
        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        users = result.scalars().all()

        return UserListResponse(
            users=[UserListItem.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
        )


@admin_router.get(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    dependencies=[Depends(require_role("master", "leader", "curator"))],
)
async def get_user(
    user_id: UUID,
    current_user: dict = Depends(get_current_user),
) -> UserDetailResponse:
    """Return full user profile with payments, completions, and referrals."""
    async with session_factory() as session:
        # Fetch user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Completions count
        completions_result = await session.execute(
            select(func.count(UserCompletion.id)).where(
                UserCompletion.user_id == user_id
            )
        )
        completions_count = completions_result.scalar() or 0

        # Payments
        payments_result = await session.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
        )
        payments = payments_result.scalars().all()

        # Referrals count
        referrals_result = await session.execute(
            select(func.count(Referral.id)).where(Referral.referrer_id == user_id)
        )
        referrals_count = referrals_result.scalar() or 0

        # Commission balance
        commission_result = await session.execute(
            select(CommissionBalance).where(CommissionBalance.user_id == user_id)
        )
        commission = commission_result.scalar_one_or_none()
        commission_balance = None
        if commission:
            commission_balance = {
                "total_earned": commission.total_earned,
                "total_pending": commission.total_pending,
                "total_paid_out": commission.total_paid_out,
            }

        # Audit log
        audit_entry = AuditLog(
            action="user_viewed",
            details=f"Viewed user {user_id}",
            admin_id=None,  # Could map from JWT if needed
        )
        session.add(audit_entry)
        await session.commit()

        return UserDetailResponse(
            id=user.id,
            telegram_id=user.telegram_id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            archetype=user.archetype,
            xp=user.xp,
            streak=user.streak,
            is_active=user.is_active,
            paid_at=user.paid_at,
            started_at=user.started_at,
            created_at=user.created_at,
            timezone=user.timezone,
            completions_count=completions_count,
            payments=[
                UserPaymentItem(
                    id=p.id,
                    amount=p.amount,
                    status=p.status,
                    created_at=p.created_at,
                )
                for p in payments
            ],
            referrals_count=referrals_count,
            commission_balance=commission_balance,
        )


# --- Commission payout endpoints ---


@admin_router.post("/payout")
async def payout(request: PayoutRequest) -> dict:
    """Process a manual commission payout for a mentor.

    Deducts from pending balance, moves to paid_out, and creates an audit
    log entry.
    """
    result = await process_payout(request.user_id, request.amount)
    if not result["success"]:
        return {"status": "error", "error": result["error"], **result}
    return {"status": "ok", **result}


@admin_router.get("/commission/{user_id}")
async def commission_balance(user_id: UUID) -> dict:
    """Query commission balance for a user."""
    balance = await get_commission_balance(user_id)
    if balance is None:
        return {"status": "error", "error": "Commission balance not found"}
    return {"status": "ok", **balance}


# --- Settings management endpoints ---


@admin_router.get(
    "/settings",
    response_model=SettingListResponse,
    dependencies=[Depends(require_role("master", "leader", "curator"))],
)
async def list_settings() -> SettingListResponse:
    """Return all platform settings as key-value pairs."""
    async with session_factory() as session:
        result = await session.execute(select(Setting).order_by(Setting.key.asc()))
        settings = result.scalars().all()
        return SettingListResponse(
            settings=[SettingResponse.model_validate(s) for s in settings]
        )


@admin_router.get(
    "/settings/{key}",
    response_model=SettingResponse,
    dependencies=[Depends(require_role("master", "leader", "curator"))],
)
async def get_setting(key: str) -> SettingResponse:
    """Return a single setting by key."""
    async with session_factory() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found",
            )
        return SettingResponse.model_validate(setting)


@admin_router.put(
    "/settings",
    response_model=SettingListResponse,
    dependencies=[Depends(require_role("master"))],
)
async def update_settings(request: SettingUpdateRequest) -> SettingListResponse:
    """Bulk update settings (upsert). Only master role can modify settings."""
    async with session_factory() as session:
        updated_keys: list[str] = []
        for item in request.settings:
            result = await session.execute(
                select(Setting).where(Setting.key == item.key)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.value = item.value
            else:
                new_setting = Setting(key=item.key, value=item.value)
                session.add(new_setting)
            updated_keys.append(item.key)

        # Audit log for settings change
        audit_entry = AuditLog(
            action="settings_updated",
            details=f"updated keys: {', '.join(updated_keys)}",
        )
        session.add(audit_entry)
        await session.commit()

        # Return updated settings
        result = await session.execute(select(Setting).order_by(Setting.key.asc()))
        settings = result.scalars().all()
        return SettingListResponse(
            settings=[SettingResponse.model_validate(s) for s in settings]
        )


# --- Audit log endpoints ---


@admin_router.get(
    "/audit",
    response_model=AuditListResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def list_audit_entries(
    action: Optional[str] = Query(None, description="Filter by action type"),
    admin_id: Optional[UUID] = Query(None, description="Filter by admin user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> AuditListResponse:
    """Return paginated audit log entries with optional filters."""
    async with session_factory() as session:
        # Base query with left join to get admin name
        query = select(AuditLog, User.username).outerjoin(
            User, AuditLog.admin_id == User.id
        )
        count_query = select(func.count(AuditLog.id))

        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)

        if admin_id:
            query = query.where(AuditLog.admin_id == admin_id)
            count_query = count_query.where(AuditLog.admin_id == admin_id)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        rows = result.all()

        entries = []
        for audit_log, admin_username in rows:
            entries.append(
                AuditEntryResponse(
                    id=audit_log.id,
                    admin_id=audit_log.admin_id,
                    admin_name=admin_username,
                    action=audit_log.action,
                    details=audit_log.details,
                    created_at=audit_log.created_at,
                )
            )

        return AuditListResponse(
            entries=entries,
            total=total,
            page=page,
            page_size=page_size,
        )


@admin_router.get(
    "/audit/{entry_id}",
    response_model=AuditEntryResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def get_audit_entry(entry_id: UUID) -> AuditEntryResponse:
    """Return a single audit log entry."""
    async with session_factory() as session:
        result = await session.execute(
            select(AuditLog, User.username)
            .outerjoin(User, AuditLog.admin_id == User.id)
            .where(AuditLog.id == entry_id)
        )
        row = result.one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit entry not found",
            )

        audit_log, admin_username = row
        return AuditEntryResponse(
            id=audit_log.id,
            admin_id=audit_log.admin_id,
            admin_name=admin_username,
            action=audit_log.action,
            details=audit_log.details,
            created_at=audit_log.created_at,
        )
