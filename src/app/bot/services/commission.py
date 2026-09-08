"""Commission calculation — configurable rate for mentor (referrer).

One-time commission: only the first succeeded payment per referee triggers commission.
Prize fund reservation: a configurable % of each succeeded payment goes to the prize fund.
Results are persisted to CommissionBalance for tracking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select

from app.bot.services.prize_fund_service import reserve_prize_fund_share
from app.shared.config import settings
from app.shared.database import session_factory
from app.shared.models.audit import AuditLog
from app.shared.models.commission import CommissionBalance
from app.shared.models.payment import Payment
from app.shared.models.user import User

logger = logging.getLogger(__name__)


async def _get_or_create_balance(
    session, user_id: UUID
) -> CommissionBalance:
    """Get or create a CommissionBalance record for a user."""
    result = await session.execute(
        select(CommissionBalance).where(CommissionBalance.user_id == user_id)
    )
    balance = result.scalar_one_or_none()
    if balance is None:
        balance = CommissionBalance(
            user_id=user_id,
            total_earned=0,
            total_pending=0,
            total_paid_out=0,
        )
        session.add(balance)
        await session.flush()
    return balance


async def calculate_commission(payment_id: UUID) -> dict:
    """Calculate mentor commission for a payment and reserve prize fund share.

    Returns:
        {"amount": int, "mentor_id": str | None, "mentor_telegram_id": int | None,
         "prize_fund_amount": int}
        - amount is 0 when payment is not succeeded, user has no mentor,
          or this is not the user's first succeeded payment (one-time commission).
        - prize_fund_amount is the amount reserved into the prize fund (0 if no fund).
    """
    async with session_factory() as session:
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()

    if payment is None:
        logger.warning("calculate_commission: payment %s not found", payment_id)
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None, "prize_fund_amount": 0}

    if payment.status != "succeeded":
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None, "prize_fund_amount": 0}

    # Load the paying user
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == payment.user_id)
        )
        user = result.scalar_one_or_none()

    if user is None:
        logger.error("calculate_commission: user %s not found", payment.user_id)
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None, "prize_fund_amount": 0}

    if user.referred_by_id is None:
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None, "prize_fund_amount": 0}

    # One-time commission: check if this is the FIRST succeeded payment for this user
    async with session_factory() as session:
        result = await session.execute(
            select(func.count()).select_from(Payment).where(
                Payment.user_id == user.id,
                Payment.status == "succeeded",
            )
        )
        succeeded_count = result.scalar_one()

    if succeeded_count > 1:
        # Not the first succeeded payment — no commission
        logger.info(
            "calculate_commission: user %s already has %d succeeded payments — skipping",
            user.id,
            succeeded_count,
        )
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None, "prize_fund_amount": 0}

    # Load the mentor (referrer)
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == user.referred_by_id)
        )
        mentor = result.scalar_one_or_none()

    if mentor is None:
        logger.error("calculate_commission: mentor %s not found", user.referred_by_id)
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None, "prize_fund_amount": 0}

    commission = int(payment.amount * settings.COMMISSION_RATE)

    # Persist commission to balance
    async with session_factory() as session:
        balance = await _get_or_create_balance(session, mentor.id)
        balance.total_pending += commission
        balance.last_commission_at = datetime.now(timezone.utc)
        await session.commit()

    # Reserve prize fund share (always, regardless of mentor)
    prize_fund_amount = await reserve_prize_fund_share(payment)

    return {
        "amount": commission,
        "mentor_id": str(mentor.id),
        "mentor_telegram_id": mentor.telegram_id,
        "prize_fund_amount": prize_fund_amount,
    }


async def process_payout(user_id: UUID, amount: int, admin_id: UUID | None = None) -> dict:
    """Process a manual commission payout for a mentor.

    Atomically deducts from pending balance, adds to paid_out, and creates
    an AuditLog entry.

    Returns:
        {"success": True, "amount": int, "new_pending": int, "new_paid_out": int}
        or {"success": False, "error": str, ...}
    """
    async with session_factory() as session:
        result = await session.execute(
            select(CommissionBalance).where(CommissionBalance.user_id == user_id)
        )
        balance = result.scalar_one_or_none()

        if balance is None:
            return {"success": False, "error": "No commission balance found"}

        if balance.total_pending < amount:
            return {
                "success": False,
                "error": "Insufficient balance",
                "pending": balance.total_pending,
            }

        balance.total_pending -= amount
        balance.total_paid_out += amount

        audit = AuditLog(
            admin_id=admin_id,
            action="commission_payout",
            details=f"user_id={user_id}, amount={amount}",
        )
        session.add(audit)

        await session.commit()

    return {
        "success": True,
        "amount": amount,
        "new_pending": balance.total_pending,
        "new_paid_out": balance.total_paid_out,
    }


async def get_commission_balance(user_id: UUID) -> dict | None:
    """Query commission balance for a user.

    Returns balance dict with earned/pending/paid_out fields, or None if
    no balance record exists.
    """
    async with session_factory() as session:
        result = await session.execute(
            select(CommissionBalance).where(CommissionBalance.user_id == user_id)
        )
        b = result.scalar_one_or_none()

    if b is None:
        return None

    return {
        "total_earned": b.total_earned,
        "total_pending": b.total_pending,
        "total_paid_out": b.total_paid_out,
        "last_commission_at": b.last_commission_at,
    }
