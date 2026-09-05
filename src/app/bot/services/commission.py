"""Commission calculation — 10% of payment amount for mentor (referrer).

Pure calculation logic — does NOT store results. Commission tracking
and balance will be added in Phase 6 (REF-06, REF-07).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.payment import Payment
from app.shared.models.user import User

logger = logging.getLogger(__name__)

# 10% commission rate — will become a settings field in Phase 6
COMMISSION_RATE = 0.10


async def calculate_commission(payment_id: UUID) -> dict:
    """Calculate mentor commission for a payment.

    Returns:
        {"amount": int, "mentor_id": str | None, "mentor_telegram_id": int | None}
        - amount is 0 when payment is not succeeded or user has no mentor.
    """
    async with session_factory() as session:
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()

    if payment is None:
        logger.warning("calculate_commission: payment %s not found", payment_id)
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None}

    if payment.status != "succeeded":
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None}

    # Load the paying user
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == payment.user_id)
        )
        user = result.scalar_one_or_none()

    if user is None:
        logger.error("calculate_commission: user %s not found", payment.user_id)
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None}

    if user.referred_by_id is None:
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None}

    # Load the mentor (referrer)
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == user.referred_by_id)
        )
        mentor = result.scalar_one_or_none()

    if mentor is None:
        logger.error("calculate_commission: mentor %s not found", user.referred_by_id)
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None}

    commission = int(payment.amount * COMMISSION_RATE)

    return {
        "amount": commission,
        "mentor_id": str(mentor.id),
        "mentor_telegram_id": mentor.telegram_id,
    }
