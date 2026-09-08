"""Prize fund service — pool management and distribution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func

from app.bot.services.settings_service import get_prize_fund_percent
from app.shared.database import session_factory
from app.shared.models.payment import Payment
from app.shared.models.prize_fund import PrizeFund, PrizeFundPayout
from app.shared.models.user import User


@dataclass
class PrizeFundStatus:
    """Current status of a prize fund."""

    fund_id: UUID
    name: str
    total_amount: int
    percent_rule: str
    status: str
    distributed_at: datetime | None


async def get_active_fund() -> PrizeFund | None:
    """Get the currently open prize fund, or None."""
    async with session_factory() as session:
        result = await session.execute(
            select(PrizeFund).where(PrizeFund.status == "open").limit(1)
        )
        return result.scalar_one_or_none()


async def create_fund(name: str, percent_rule: str = "xp") -> PrizeFund:
    """Create a new open prize fund."""
    async with session_factory() as session:
        fund = PrizeFund(name=name, percent_rule=percent_rule, status="open")
        session.add(fund)
        await session.commit()
        await session.refresh(fund)
        return fund


async def reserve_prize_fund_share(payment: Payment) -> int:
    """Reserve a percentage of a confirmed payment into the active prize fund.

    Returns the amount reserved in kopecks.
    """
    percent = await get_prize_fund_percent()
    amount = payment.amount * percent // 10000  # percent is in basis points (500 = 5%)

    fund = await get_active_fund()
    if fund is None:
        # Create default fund if none exists
        fund = await create_fund("Default Prize Fund")

    async with session_factory() as session:
        fund.total_amount += amount
        await session.commit()

    return amount


async def distribute_fund(fund_id: UUID, top_n: int = 10) -> list[PrizeFundPayout]:
    """Distribute the prize fund among top N users by XP.

    Updates fund status to 'distributed' and records payout rows.
    """
    fund = await get_fund_by_id(fund_id)
    if fund is None or fund.status != "open":
        return []

    async with session_factory() as session:
        # Get top N users by XP
        result = await session.execute(
            select(User).order_by(User.xp.desc()).limit(top_n)
        )
        top_users = list(result.scalars().all())

        if not top_users:
            return []

        # Equal split for now (can be weighted by XP/streak per rule)
        payout_amount = fund.total_amount // len(top_users)

        payouts = []
        for user in top_users:
            payout = PrizeFundPayout(
                prize_fund_id=fund_id,
                user_id=user.id,
                amount=payout_amount,
                paid_at=datetime.now(timezone.utc),
            )
            session.add(payout)
            payouts.append(payout)

        fund.status = "distributed"
        fund.distributed_at = datetime.now(timezone.utc)
        await session.commit()

        return payouts


async def get_fund_by_id(fund_id: UUID) -> PrizeFund | None:
    """Get a prize fund by ID."""
    async with session_factory() as session:
        result = await session.execute(select(PrizeFund).where(PrizeFund.id == fund_id))
        return result.scalar_one_or_none()


async def get_fund_status(fund_id: UUID) -> PrizeFundStatus | None:
    """Get formatted status of a prize fund."""
    fund = await get_fund_by_id(fund_id)
    if fund is None:
        return None

    return PrizeFundStatus(
        fund_id=fund.id,
        name=fund.name,
        total_amount=fund.total_amount,
        percent_rule=fund.percent_rule,
        status=fund.status,
        distributed_at=fund.distributed_at,
    )


async def get_fund_payouts(fund_id: UUID) -> list[PrizeFundPayout]:
    """Get all payouts for a prize fund."""
    async with session_factory() as session:
        result = await session.execute(
            select(PrizeFundPayout).where(PrizeFundPayout.prize_fund_id == fund_id)
        )
        return list(result.scalars().all())