"""Admin API endpoints — user management, commission payout and balance query."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_role
from app.bot.services.commission import get_commission_balance, process_payout
from app.shared.database import session_factory
from app.shared.models.audit import AuditLog
from app.shared.models.commission import CommissionBalance
from app.shared.models.completion import UserCompletion
from app.shared.models.payment import Payment
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
