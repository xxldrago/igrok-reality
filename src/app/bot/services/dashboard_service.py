"""Dashboard service — aggregate KPIs for the admin dashboard."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.shared.database import session_factory
from app.shared.models.completion import UserCompletion
from app.shared.models.daily_scroll import DailyScroll
from app.shared.models.payment import Payment
from app.shared.models.prize_fund import PrizeFund
from app.shared.models.scroll import Scroll
from app.shared.models.user import User

# Successful payment status stored by the provider webhooks/finalize flow.
PAID_STATUS = "succeeded"


async def compute_dashboard() -> dict[str, Any]:
    """Compute admin dashboard KPIs.

    Returns:
        active_players: users with archetype set (registered)
        paid_players: users with at least one successful payment
        conversion_rate: paid / active (0.0 if no active)
        total_income: sum of successful payment amounts (kopecks)
        prize_fund_total: sum of all prize fund amounts
        retention_by_day: dict[day_number] = completion count
        recent_activity: last 10 completions with user info
    """
    async with session_factory() as session:
        # Active players (registered, archetype set)
        active_result = await session.execute(
            select(func.count(User.id)).where(User.archetype.isnot(None))
        )
        active_players = active_result.scalar() or 0

        # Paid players (at least one successful payment)
        paid_result = await session.execute(
            select(func.count(func.distinct(Payment.user_id))).where(
                Payment.status == PAID_STATUS
            )
        )
        paid_players = paid_result.scalar() or 0

        # Total income (sum of successful payments)
        income_result = await session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == PAID_STATUS
            )
        )
        total_income = income_result.scalar() or 0

        # Prize fund total
        fund_result = await session.execute(
            select(func.coalesce(func.sum(PrizeFund.total_amount), 0))
        )
        prize_fund_total = fund_result.scalar() or 0

        # Retention by quest day (completions per day_number, full history:
        # the quest spans 90 days, a narrow window hides most of the funnel).
        # UserCompletion.scroll_id is polymorphic: current completions point at
        # DailyScroll, legacy rows at Scroll — outer-join both and coalesce.
        day_number_col = func.coalesce(DailyScroll.day_number, Scroll.day_number)
        retention_result = await session.execute(
            select(
                day_number_col.label("day_number"),
                func.count(UserCompletion.id),
            )
            .outerjoin(DailyScroll, UserCompletion.scroll_id == DailyScroll.id)
            .outerjoin(Scroll, UserCompletion.scroll_id == Scroll.id)
            .group_by(day_number_col)
            .order_by(day_number_col)
        )
        retention_by_day = {
            row[0]: row[1] for row in retention_result.all() if row[0] is not None
        }

        # Recent activity (last 10 completions)
        recent_result = await session.execute(
            select(
                UserCompletion,
                User.username,
                User.first_name,
                day_number_col.label("day_number"),
            )
            .join(User, UserCompletion.user_id == User.id)
            .outerjoin(DailyScroll, UserCompletion.scroll_id == DailyScroll.id)
            .outerjoin(Scroll, UserCompletion.scroll_id == Scroll.id)
            .order_by(UserCompletion.completed_at.desc())
            .limit(10)
        )
        recent_activity = []
        for completion, username, first_name, day_number in recent_result.all():
            recent_activity.append(
                {
                    "user_name": username or first_name or "—",
                    "day_number": day_number or 0,
                    "xp_awarded": completion.xp_awarded,
                    "created_at": completion.completed_at.isoformat()
                    if completion.completed_at
                    else "",
                }
            )

        conversion_rate = (paid_players / active_players * 100) if active_players > 0 else 0.0

        return {
            "active_players": active_players,
            "paid_players": paid_players,
            "conversion_rate": round(conversion_rate, 1),
            "total_income": total_income,
            "prize_fund_total": prize_fund_total,
            "retention_by_day": retention_by_day,
            "recent_activity": recent_activity,
        }
