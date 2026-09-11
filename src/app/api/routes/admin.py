"""Admin API endpoints — user management, scroll CRUD, payment list, settings, audit, commission payout."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_user, require_role
from app.bot.services.commission import get_commission_balance, process_payout
from app.bot.services.dashboard_service import compute_dashboard
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

    model_config = ConfigDict(from_attributes=True)

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
    role: str = "player"


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

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

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


# --- Dashboard Pydantic models ---


class DashboardResponse(BaseModel):
    """Admin dashboard KPIs."""

    active_players: int
    paid_players: int
    conversion_rate: float
    total_income: int
    prize_fund_total: int
    retention_by_day: dict[int, int]
    recent_activity: list[dict]


# --- Finance Pydantic models ---


class CommissionBalanceResponse(BaseModel):
    """Mentor commission balance."""

    user_id: UUID
    username: Optional[str] = None
    pending: int
    paid_out: int
    last_commission_at: Optional[datetime] = None


class CommissionListResponse(BaseModel):
    """List of mentor commission balances."""

    balances: list[CommissionBalanceResponse]


class PrizeFundResponse(BaseModel):
    """Prize fund status."""

    id: UUID
    name: str
    total_amount: int
    percent_rule: str
    status: str
    distributed_at: Optional[datetime] = None
    created_at: datetime


class PrizeFundListResponse(BaseModel):
    """List of prize funds."""

    funds: list[PrizeFundResponse]


class PrizeFundCreateRequest(BaseModel):
    """Request body for creating a prize fund."""

    name: str = Field(min_length=1, description="Fund name")
    percent_rule: int = Field(ge=1, le=100, description="Percent of payments")


class PrizeFundDistributeRequest(BaseModel):
    """Request body for distributing a prize fund."""

    fund_id: UUID
    top_n: int = Field(ge=1, le=100, default=10, description="Top N users by XP")


# --- Moderation Pydantic models ---


class ModerationReportResponse(BaseModel):
    """Moderation report entry."""

    id: UUID
    user_id: UUID
    username: Optional[str] = None
    reason: str
    status: str
    created_at: datetime


class ModerationListResponse(BaseModel):
    """List of moderation reports."""

    reports: list[ModerationReportResponse]
    total: int


class ModerationResolveRequest(BaseModel):
    """Request body for resolving a moderation report."""

    decision: str = Field(description="warn, ban, or exclude")


# --- Role change Pydantic models ---


class RoleChangeRequest(BaseModel):
    """Request body for changing a user's role."""

    role: str = Field(description="New role: master, leader, curator, specialist, player")


class RoleChangeResponse(BaseModel):
    """Response after role change."""

    user_id: UUID
    old_role: Optional[str] = None
    new_role: str
    changed_at: datetime


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


# --- Dashboard endpoint ---


@admin_router.get(
    "/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def get_dashboard() -> DashboardResponse:
    """Return admin dashboard KPIs."""
    data = await compute_dashboard()
    return DashboardResponse(**data)


# --- Finance endpoints ---


@admin_router.get(
    "/commissions",
    response_model=CommissionListResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def list_commissions() -> CommissionListResponse:
    """List all mentor commission balances."""
    async with session_factory() as session:
        result = await session.execute(
            select(CommissionBalance, User.username)
            .outerjoin(User, CommissionBalance.user_id == User.id)
            .order_by(CommissionBalance.total_pending.desc())
        )
        rows = result.all()
        balances = []
        for balance, username in rows:
            balances.append(
                CommissionBalanceResponse(
                    user_id=balance.user_id,
                    username=username,
                    pending=balance.pending,
                    paid_out=balance.paid_out,
                    last_commission_at=balance.last_commission_at,
                )
            )
        return CommissionListResponse(balances=balances)


@admin_router.get(
    "/prize-funds",
    response_model=PrizeFundListResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def list_prize_funds() -> PrizeFundListResponse:
    """List all prize funds."""
    from app.shared.models.prize_fund import PrizeFund as PrizeFundModel

    async with session_factory() as session:
        result = await session.execute(
            select(PrizeFundModel).order_by(PrizeFundModel.created_at.desc())
        )
        funds = result.scalars().all()
        return PrizeFundListResponse(
            funds=[
                PrizeFundResponse(
                    id=f.id,
                    name=f.name,
                    total_amount=f.total_amount,
                    percent_rule=f.percent_rule,
                    status=f.status,
                    distributed_at=f.distributed_at,
                    created_at=f.created_at,
                )
                for f in funds
            ]
        )


@admin_router.post(
    "/prize-funds",
    response_model=PrizeFundResponse,
    dependencies=[Depends(require_role("master"))],
)
async def create_prize_fund(req: PrizeFundCreateRequest) -> PrizeFundResponse:
    """Create a new prize fund."""
    from app.bot.services.prize_fund_service import create_fund

    fund = await create_fund(req.name, req.percent_rule)
    return PrizeFundResponse(
        id=fund.id,
        name=fund.name,
        total_amount=fund.total_amount,
        percent_rule=fund.percent_rule,
        status=fund.status,
        distributed_at=fund.distributed_at,
        created_at=fund.created_at,
    )


@admin_router.post(
    "/prize-funds/distribute",
    dependencies=[Depends(require_role("master"))],
)
async def distribute_prize_fund(req: PrizeFundDistributeRequest) -> dict:
    """Distribute a prize fund among top users."""
    from app.bot.services.prize_fund_service import distribute_fund

    payouts = await distribute_fund(req.fund_id, req.top_n)
    return {"distributed": len(payouts), "fund_id": str(req.fund_id)}


@admin_router.get(
    "/payments/export",
    dependencies=[Depends(require_role("master"))],
)
async def export_payments_csv() -> dict:
    """Export confirmed payments as CSV data for accounting."""
    async with session_factory() as session:
        result = await session.execute(
            select(Payment, User.username, User.first_name)
            .outerjoin(User, Payment.user_id == User.id)
            .where(Payment.status == "confirmed")
            .order_by(Payment.created_at.desc())
        )
        rows = result.all()
        csv_lines = ["id,user_name,amount,currency,method,created_at"]
        for payment, username, first_name in rows:
            name = username or first_name or "—"
            csv_lines.append(
                f"{payment.id},{name},{payment.amount},{payment.currency},"
                f"{payment.payment_method or '—'},{payment.created_at.isoformat()}"
            )
        return {"csv": "\n".join(csv_lines), "count": len(rows)}


# --- Moderation endpoints ---


@admin_router.get(
    "/moderation",
    response_model=ModerationListResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def list_moderation_reports(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
) -> ModerationListResponse:
    """List moderation reports."""
    from app.shared.models.moderation_report import ModerationReport

    async with session_factory() as session:
        query = select(ModerationReport, User.username).outerjoin(
            User, ModerationReport.user_id == User.id
        )
        count_query = select(func.count(ModerationReport.id))

        if status_filter:
            query = query.where(ModerationReport.status == status_filter)
            count_query = count_query.where(ModerationReport.status == status_filter)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(ModerationReport.created_at.desc())
        result = await session.execute(query)
        rows = result.all()

        reports = []
        for report, username in rows:
            reports.append(
                ModerationReportResponse(
                    id=report.id,
                    user_id=report.user_id,
                    username=username,
                    reason=report.reason,
                    status=report.status,
                    created_at=report.created_at,
                )
            )
        return ModerationListResponse(reports=reports, total=total)


@admin_router.post(
    "/moderation/{report_id}/resolve",
    dependencies=[Depends(require_role("master"))],
)
async def resolve_moderation_report(
    report_id: UUID, req: ModerationResolveRequest
) -> dict:
    """Resolve a moderation report with a decision (warn/ban/exclude)."""
    from app.shared.models.moderation_report import ModerationReport

    if req.decision not in ("warn", "ban", "exclude"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be warn, ban, or exclude",
        )

    async with session_factory() as session:
        result = await session.execute(
            select(ModerationReport).where(ModerationReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found",
            )

        report.status = req.decision
        await session.commit()

        # Log the action
        audit = AuditLog(
            admin_id=None,  # Will be set by middleware if available
            action="moderation_resolve",
            details=f"Report {report_id} resolved: {req.decision}",
        )
        session.add(audit)
        await session.commit()

        return {"report_id": str(report_id), "decision": req.decision}


# --- Role change endpoint ---


@admin_router.post(
    "/users/{user_id}/role",
    response_model=RoleChangeResponse,
    dependencies=[Depends(require_role("master"))],
)
async def change_user_role(user_id: UUID, req: RoleChangeRequest) -> RoleChangeResponse:
    """Change a user's role (master-only, records history + audit)."""
    from app.bot.services.role_service import change_role
    from datetime import datetime, timezone

    old_role, new_role = await change_role(user_id, req.role, admin_id=None)
    return RoleChangeResponse(
        user_id=user_id,
        old_role=old_role,
        new_role=new_role,
        changed_at=datetime.now(timezone.utc),
    )


# --- Scroll Types endpoints ---


class ScrollTypeResponse(BaseModel):
    """Scroll type info."""

    id: UUID
    code: str
    name: str
    command: str
    hour: int
    minute: int
    xp_reward: int
    description: str
    requires_meditation: bool
    is_breathing_day_only: bool
    is_awareness_day_only: bool
    sort_order: int


class ScrollTypeListResponse(BaseModel):
    """List of scroll types."""

    scroll_types: list[ScrollTypeResponse]


@admin_router.get(
    "/scroll-types",
    response_model=ScrollTypeListResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def list_scroll_types() -> ScrollTypeListResponse:
    """List all scroll types."""
    from app.shared.models.scroll_type import ScrollType as ScrollTypeModel

    async with session_factory() as session:
        result = await session.execute(
            select(ScrollTypeModel).order_by(ScrollTypeModel.sort_order)
        )
        types = result.scalars().all()
        return ScrollTypeListResponse(
            scroll_types=[
                ScrollTypeResponse(
                    id=st.id,
                    code=st.code,
                    name=st.name,
                    command=st.command,
                    hour=st.hour,
                    minute=st.minute,
                    xp_reward=st.xp_reward,
                    description=st.description,
                    requires_meditation=st.requires_meditation,
                    is_breathing_day_only=st.is_breathing_day_only,
                    is_awareness_day_only=st.is_awareness_day_only,
                    sort_order=st.sort_order,
                )
                for st in types
            ]
        )


# --- Daily Scrolls endpoints ---


class DailyScrollResponse(BaseModel):
    """Daily scroll content."""

    id: UUID
    day_number: int
    scroll_type_id: UUID
    scroll_type_code: Optional[str] = None
    title: str
    content: str
    media_file_id: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime


class DailyScrollListResponse(BaseModel):
    """Paginated daily scrolls response."""

    scrolls: list[DailyScrollResponse]
    total: int
    page: int
    page_size: int


class DailyScrollUpdateRequest(BaseModel):
    """Request body for updating daily scroll content."""

    title: Optional[str] = None
    content: Optional[str] = None
    media_file_id: Optional[str] = None


@admin_router.get(
    "/daily-scrolls",
    response_model=DailyScrollListResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def list_daily_scrolls(
    day_number: Optional[int] = Query(None, description="Filter by day number"),
    scroll_type_id: Optional[UUID] = Query(None, description="Filter by scroll type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> DailyScrollListResponse:
    """List daily scrolls with optional filters."""
    from app.shared.models.daily_scroll import DailyScroll as DailyScrollModel
    from app.shared.models.scroll_type import ScrollType as ScrollTypeModel

    async with session_factory() as session:
        query = select(DailyScrollModel, ScrollTypeModel.code).outerjoin(
            ScrollTypeModel, DailyScrollModel.scroll_type_id == ScrollTypeModel.id
        )
        count_query = select(func.count(DailyScrollModel.id))

        if day_number is not None:
            query = query.where(DailyScrollModel.day_number == day_number)
            count_query = count_query.where(DailyScrollModel.day_number == day_number)
        if scroll_type_id is not None:
            query = query.where(DailyScrollModel.scroll_type_id == scroll_type_id)
            count_query = count_query.where(DailyScrollModel.scroll_type_id == scroll_type_id)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(DailyScrollModel.day_number, DailyScrollModel.scroll_type_id)
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        rows = result.all()

        scrolls = []
        for ds, type_code in rows:
            scrolls.append(
                DailyScrollResponse(
                    id=ds.id,
                    day_number=ds.day_number,
                    scroll_type_id=ds.scroll_type_id,
                    scroll_type_code=type_code,
                    title=ds.title,
                    content=ds.content,
                    media_file_id=ds.media_file_id,
                    published_at=ds.published_at,
                    created_at=ds.created_at,
                )
            )

        return DailyScrollListResponse(
            scrolls=scrolls, total=total, page=page, page_size=page_size
        )


@admin_router.put(
    "/daily-scrolls/{scroll_id}",
    dependencies=[Depends(require_role("master", "leader"))],
)
async def update_daily_scroll(
    scroll_id: UUID, req: DailyScrollUpdateRequest
) -> dict:
    """Update daily scroll content."""
    from app.shared.models.daily_scroll import DailyScroll as DailyScrollModel

    async with session_factory() as session:
        result = await session.execute(
            select(DailyScrollModel).where(DailyScrollModel.id == scroll_id)
        )
        ds = result.scalar_one_or_none()
        if ds is None:
            raise HTTPException(status_code=404, detail="Daily scroll not found")

        if req.title is not None:
            ds.title = req.title
        if req.content is not None:
            ds.content = req.content
        if req.media_file_id is not None:
            ds.media_file_id = req.media_file_id

        await session.commit()
        return {"id": str(scroll_id), "updated": True}


# --- User Daily Commands endpoint ---


class UserCommandResponse(BaseModel):
    """User daily command record."""

    id: UUID
    user_id: UUID
    quest_day: int
    command: str
    xp_awarded: int
    completed_at: datetime
    report_text: Optional[str] = None


class UserCommandListResponse(BaseModel):
    """List of user commands."""

    commands: list[UserCommandResponse]
    total: int


@admin_router.get(
    "/users/{user_id}/commands",
    response_model=UserCommandListResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def list_user_commands(
    user_id: UUID,
    quest_day: Optional[int] = Query(None, description="Filter by quest day"),
) -> UserCommandListResponse:
    """List a user's daily command completions."""
    from app.shared.models.user_daily_command import UserDailyCommand

    async with session_factory() as session:
        query = select(UserDailyCommand).where(UserDailyCommand.user_id == user_id)
        count_query = select(func.count(UserDailyCommand.id)).where(
            UserDailyCommand.user_id == user_id
        )

        if quest_day is not None:
            query = query.where(UserDailyCommand.quest_day == quest_day)
            count_query = count_query.where(UserDailyCommand.quest_day == quest_day)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(UserDailyCommand.completed_at.desc())
        result = await session.execute(query)
        commands = result.scalars().all()

        return UserCommandListResponse(
            commands=[
                UserCommandResponse(
                    id=c.id,
                    user_id=c.user_id,
                    quest_day=c.quest_day,
                    command=c.command,
                    xp_awarded=c.xp_awarded,
                    completed_at=c.completed_at,
                    report_text=c.report_text,
                )
                for c in commands
            ],
            total=total,
        )


# --- Quiz management endpoints ---


class QuizOptionRequest(BaseModel):
    """Single quiz option."""

    text: str = Field(min_length=1)
    key: str = Field(min_length=1, max_length=1)


class QuizQuestionRequest(BaseModel):
    """Quiz question with options."""

    text: str = Field(min_length=1)
    options: list[QuizOptionRequest]


class QuizConfigRequest(BaseModel):
    """Full quiz configuration."""

    intro: str
    questions: list[QuizQuestionRequest]


class QuizQuestionResponse(BaseModel):
    """Quiz question response."""

    text: str
    options: list[dict[str, str]]


class QuizConfigResponse(BaseModel):
    """Quiz configuration response."""

    intro: str
    questions: list[QuizQuestionResponse]
    results: dict[str, str]


class ArchetypeScoresRequest(BaseModel):
    """Archetype scoring configuration."""

    scores: dict[str, dict[str, int]]  # e.g. {"1": {"a": {"head": 2}, ...}}


@admin_router.get(
    "/quiz",
    response_model=QuizConfigResponse,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def get_quiz_config() -> QuizConfigResponse:
    """Get current quiz configuration."""
    import json
    async with session_factory() as session:
        intro = await session.execute(select(Setting).where(Setting.key == "quiz_intro"))
        intro = intro.scalar_one_or_none()
        
        questions_json = await session.execute(select(Setting).where(Setting.key == "quiz_questions"))
        questions_json = questions_json.scalar_one_or_none()
        
        results_json = await session.execute(select(Setting).where(Setting.key == "quiz_results"))
        results_json = results_json.scalar_one_or_none()
    
    questions = []
    if questions_json and questions_json.value:
        try:
            questions_data = json.loads(questions_json.value)
            for q in questions_data:
                questions.append(QuizQuestionResponse(
                    text=q["text"],
                    options=q["options"]
                ))
        except Exception:
            pass
    
    results = {}
    if results_json and results_json.value:
        try:
            results = json.loads(results_json.value)
        except Exception:
            pass
    
    return QuizConfigResponse(
        intro=intro.value if intro else "",
        questions=questions,
        results=results,
    )


@admin_router.put(
    "/quiz",
    dependencies=[Depends(require_role("master"))],
)
async def update_quiz_config(req: QuizConfigRequest) -> dict:
    """Update quiz configuration (intro, questions)."""
    import json
    async with session_factory() as session:
        # Update intro
        intro_setting = await session.execute(select(Setting).where(Setting.key == "quiz_intro"))
        intro_setting = intro_setting.scalar_one_or_none()
        if intro_setting is None:
            intro_setting = Setting(key="quiz_intro", value=req.intro)
            session.add(intro_setting)
        else:
            intro_setting.value = req.intro
        
        # Update questions
        questions_setting = await session.execute(select(Setting).where(Setting.key == "quiz_questions"))
        questions_setting = questions_setting.scalar_one_or_none()
        questions_json = json.dumps([
            {"text": q.text, "options": [opt.model_dump() for opt in q.options]}
            for q in req.questions
        ])
        if questions_setting is None:
            questions_setting = Setting(key="quiz_questions", value=questions_json)
            session.add(questions_setting)
        else:
            questions_setting.value = questions_json
        
        await session.commit()
        return {"updated": True}


@admin_router.get(
    "/quiz/results",
    response_model=dict[str, str],
    dependencies=[Depends(require_role("master", "leader"))],
)
async def get_quiz_results() -> dict[str, str]:
    """Get quiz results for all archetypes."""
    import json
    async with session_factory() as session:
        results_json = await session.execute(select(Setting).where(Setting.key == "quiz_results"))
        results_json = results_json.scalar_one_or_none()
    
    if results_json and results_json.value:
        try:
            return json.loads(results_json.value)
        except Exception:
            pass
    return {}


@admin_router.put(
    "/quiz/results",
    dependencies=[Depends(require_role("master"))],
)
async def update_quiz_results(req: dict[str, str]) -> dict:
    """Update quiz results for archetypes."""
    import json
    async with session_factory() as session:
        results_setting = await session.execute(select(Setting).where(Setting.key == "quiz_results"))
        results_setting = results_setting.scalar_one_or_none()
        results_json = json.dumps(req)
        if results_setting is None:
            results_setting = Setting(key="quiz_results", value=results_json)
            session.add(results_setting)
        else:
            results_setting.value = results_json
        await session.commit()
        return {"updated": True}


@admin_router.get(
    "/quiz/scores",
    response_model=dict,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def get_archetype_scores() -> dict:
    """Get archetype scoring configuration."""
    import json
    async with session_factory() as session:
        scores_json = await session.execute(select(Setting).where(Setting.key == "archetype_scores"))
        scores_json = scores_json.scalar_one_or_none()
    
    if scores_json and scores_json.value:
        try:
            return json.loads(scores_json.value)
        except Exception:
            pass
    return {}


@admin_router.put(
    "/quiz/scores",
    dependencies=[Depends(require_role("master"))],
)
async def update_archetype_scores(req: ArchetypeScoresRequest) -> dict:
    """Update archetype scoring configuration."""
    import json
    async with session_factory() as session:
        scores_setting = await session.execute(select(Setting).where(Setting.key == "archetype_scores"))
        scores_setting = scores_setting.scalar_one_or_none()
        scores_json = json.dumps(req.scores)
        if scores_setting is None:
            scores_setting = Setting(key="archetype_scores", value=scores_json)
            session.add(scores_setting)
        else:
            scores_setting.value = scores_json
        await session.commit()
        return {"updated": True}


# --- Broadcast endpoints ---


class BroadcastRequest(BaseModel):
    """Request body for broadcast message."""

    text: str = Field(min_length=1, max_length=4000, description="Message text")
    archetype: Optional[str] = Field(None, description="Filter by archetype: head, shell, whirlwind, ghost. Null = all.")
    parse_mode: Optional[str] = Field(None, description="Telegram parse_mode: Markdown, HTML")


class BroadcastResponse(BaseModel):
    """Broadcast response."""

    sent: int
    failed: int
    total: int


@admin_router.post(
    "/broadcast",
    response_model=BroadcastResponse,
    dependencies=[Depends(require_role("master"))],
)
async def send_broadcast(req: BroadcastRequest) -> BroadcastResponse:
    """Send a broadcast message to users, optionally filtered by archetype."""
    from app.bot.services.notification_service import send_system_notification_to_all
    from sqlalchemy import select

    async with session_factory() as session:
        query = select(User).where(User.archetype.isnot(None), User.started_at.isnot(None))
        if req.archetype:
            query = query.where(User.archetype == req.archetype)
        result = await session.execute(query)
        users = list(result.scalars().all())

    if not users:
        return BroadcastResponse(sent=0, failed=0, total=0)

    # Create notifications
    notifications = []
    async with session_factory() as session:
        for user in users:
            notification = Notification(
                user_id=user.id,
                type="broadcast",
                payload=req.text,
            )
            session.add(notification)
            notifications.append(notification)
        await session.commit()

    # Send via ARQ worker (async, non-blocking)
    # Notifications are queued and will be sent by send_pending_notifications worker
    return BroadcastResponse(sent=len(notifications), failed=0, total=len(notifications))


# --- User create / update endpoints ---


class UserCreateRequest(BaseModel):
    """Request body for creating a user manually."""

    model_config = ConfigDict(from_attributes=True)

    telegram_id: int = Field(description="Telegram user ID (must be unique)")
    first_name: str = Field(min_length=1, description="First name")
    last_name: Optional[str] = None
    username: Optional[str] = Field(None, description="Telegram username without @")
    archetype: Optional[str] = Field(None, description="head, shell, whirlwind, ghost")
    xp: int = Field(default=0, ge=0)
    streak: int = Field(default=0, ge=0)
    is_active: bool = True
    timezone: str = "Asia/Krasnoyarsk"
    role: str = Field(default="player", description="player, curator, specialist, leader, master")


class UserUpdateRequest(BaseModel):
    """Request body for updating a user (all fields optional)."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = Field(None, description="Telegram username without @")
    archetype: Optional[str] = Field(None, description="head, shell, whirlwind, ghost (null clears)")
    xp: Optional[int] = Field(None, ge=0)
    streak: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    timezone: Optional[str] = None
    role: Optional[str] = Field(None, description="player, curator, specialist, leader, master")
    has_paid: Optional[bool] = Field(None, description="True grants access (sets paid_at), False revokes it")


@admin_router.post(
    "/users",
    response_model=UserListItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def create_user_admin(req: UserCreateRequest) -> UserListItem:
    """Create a user manually (e.g. for testing or manual onboarding)."""
    from datetime import datetime, timezone
    from app.bot.services.user_service import generate_referral_code

    if req.archetype is not None and req.archetype not in VALID_ARCHETYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"archetype must be one of {VALID_ARCHETYPES}",
        )

    from app.bot.services.role_service import VALID_ROLES
    if req.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role must be one of {sorted(VALID_ROLES)}",
        )

    username = req.username.strip().lstrip("@") if req.username else None

    async with session_factory() as session:
        existing = await session.execute(
            select(User).where(User.telegram_id == req.telegram_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with telegram_id {req.telegram_id} already exists",
            )

        user = User(
            telegram_id=req.telegram_id,
            first_name=req.first_name.strip(),
            last_name=req.last_name.strip() if req.last_name else None,
            username=username or None,
            archetype=req.archetype,
            xp=req.xp,
            streak=req.streak,
            is_active=req.is_active,
            timezone=req.timezone,
            role=req.role,
            referral_code=generate_referral_code(),
            started_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.add(AuditLog(action="user_created", details=f"telegram_id={req.telegram_id}"))
        await session.commit()
        await session.refresh(user)
        return UserListItem.model_validate(user)


@admin_router.put(
    "/users/{user_id}",
    response_model=UserListItem,
    dependencies=[Depends(require_role("master", "leader"))],
)
async def update_user_admin(user_id: UUID, req: UserUpdateRequest) -> UserListItem:
    """Update user fields (profile, archetype, XP, streak, status, role, access)."""
    from datetime import datetime, timezone

    if req.archetype is not None and req.archetype not in VALID_ARCHETYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"archetype must be one of {VALID_ARCHETYPES}",
        )

    if req.role is not None:
        from app.bot.services.role_service import VALID_ROLES
        if req.role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"role must be one of {sorted(VALID_ROLES)}",
            )

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if req.first_name is not None:
            user.first_name = req.first_name.strip()
        if req.last_name is not None:
            user.last_name = req.last_name.strip() or None
        if req.username is not None:
            cleaned = req.username.strip().lstrip("@")
            user.username = cleaned or None
        if req.archetype is not None:
            user.archetype = req.archetype
        if req.xp is not None:
            user.xp = req.xp
        if req.streak is not None:
            user.streak = req.streak
        if req.is_active is not None:
            user.is_active = req.is_active
        if req.timezone is not None:
            user.timezone = req.timezone.strip() or user.timezone
        if req.role is not None:
            user.role = req.role
        if req.has_paid is True and user.paid_at is None:
            user.paid_at = datetime.now(timezone.utc)
        elif req.has_paid is False:
            user.paid_at = None

        session.add(AuditLog(action="user_updated", details=f"Updated user {user_id}"))
        await session.commit()
        await session.refresh(user)
        return UserListItem.model_validate(user)


# --- Extended settings schema endpoint ---


@admin_router.get(
    "/settings-schema",
    dependencies=[Depends(require_role("master", "leader"))],
)
async def get_settings_schema() -> dict:
    """Return grouped editable settings with effective values for the admin panel."""
    from app.bot.services.settings_service import get_settings_schema as load_schema

    return {"groups": await load_schema()}


@admin_router.get(
    "/users/archetype-stats",
    dependencies=[Depends(require_role("master", "leader"))],
)
async def get_archetype_stats() -> dict:
    """Get user count per archetype for broadcast targeting."""
    from sqlalchemy import func
    from app.shared.models.user import User as UserModel

    async with session_factory() as session:
        result = await session.execute(
            select(UserModel.archetype, func.count(UserModel.id))
            .where(UserModel.archetype.isnot(None), UserModel.started_at.isnot(None))
            .group_by(UserModel.archetype)
        )
        stats = {row[0]: row[1] for row in result.all()}
        total = sum(stats.values())
        return {"total": total, "by_archetype": stats}
