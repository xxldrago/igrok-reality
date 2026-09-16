"""Commission handler — /balance for curators/leaders/specialists."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.services.team_service import MENTOR_ROLES
from app.bot.services.user_service import get_user_by_telegram_id
from app.shared.database import session_factory
from app.shared.models.commission import CommissionBalance
from sqlalchemy import select

router = Router(name="commission")


def _fmt_kopecks(amount: int) -> str:
    """Format kopecks as readable ruble amount."""
    rub = amount // 100
    kop = amount % 100
    return f"{rub}₽ {kop:02d}"


@router.message(Command("balance"))
async def balance_handler(message: Message) -> None:
    """Show commission balance for curators/leaders/specialists."""
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return

    if user.role not in MENTOR_ROLES:
        await message.answer("Команда доступна только кураторам, лидерам и специалистам.")
        return

    async with session_factory() as session:
        result = await session.execute(
            select(CommissionBalance).where(CommissionBalance.user_id == user.id)
        )
        bal = result.scalar_one_or_none()

    if bal is None:
        await message.answer(
            "💰 Ваш баланс комиссий: 0₽\n\n"
            "Комиссия начисляется за первого оплатившего реферала."
        )
        return

    text = (
        f"💰 *Баланс комиссий*\n\n"
        f"Заработано: {_fmt_kopecks(bal.total_earned)}\n"
        f"Ожидает: {_fmt_kopecks(bal.total_pending)}\n"
        f"Выплачено: {_fmt_kopecks(bal.total_paid_out)}\n\n"
        f"Последнее начисление: {bal.last_commission_at.strftime('%d.%m.%Y %H:%M') if bal.last_commission_at else 'нет'}"
    )
    await message.answer(text, parse_mode="Markdown")
