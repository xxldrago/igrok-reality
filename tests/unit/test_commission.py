"""Tests for commission calculation — 10% rate, status and referral checks."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.commission import calculate_commission
from app.shared.models.payment import Payment
from app.shared.models.user import User


def _make_payment(
    *,
    user_id: uuid4 | None = None,
    status: str = "succeeded",
    amount: int = 4900,
) -> Payment:
    payment = Payment(
        user_id=user_id or uuid4(),
        amount=amount,
        status=status,
        idempotency_key="key",
    )
    payment.id = uuid4()
    return payment


def _make_user(
    *,
    referred_by_id: uuid4 | None = None,
    telegram_id: int = 12345,
) -> User:
    user = User(
        telegram_id=telegram_id,
        first_name="Test",
        username="testuser",
        referred_by_id=referred_by_id,
    )
    user.id = uuid4()
    return user


@patch("app.bot.services.commission.reserve_prize_fund_share")
@patch("app.bot.services.commission.session_factory")
async def test_calculate_commission_succeeded_with_mentor(
    mock_session_factory: MagicMock,
    mock_reserve: AsyncMock,
) -> None:
    """calculate_commission returns 10% for succeeded payment with mentor."""
    mock_reserve.return_value = 245  # 5% of 4900
    mentor = _make_user(telegram_id=99999)
    user = _make_user(referred_by_id=mentor.id, telegram_id=11111)
    payment = _make_payment(user_id=user.id, status="succeeded", amount=4900)

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    async def side_effect(query):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Payment lookup
            result.scalar_one_or_none.return_value = payment
        elif call_count == 2:
            # User lookup
            result.scalar_one_or_none.return_value = user
        elif call_count == 3:
            # Payment count query (first succeeded)
            result.scalar_one.return_value = 1
        elif call_count == 4:
            # Mentor lookup
            result.scalar_one_or_none.return_value = mentor
        else:
            # Balance lookup — no existing balance
            result.scalar_one_or_none.return_value = None
        return result

    mock_session.execute = AsyncMock(side_effect=side_effect)

    result = await calculate_commission(payment.id)

    assert result["amount"] == 490  # 4900 * 0.10
    assert result["mentor_id"] == str(mentor.id)
    assert result["mentor_telegram_id"] == 99999
    assert result["prize_fund_amount"] == 245


@patch("app.bot.services.commission.session_factory")
async def test_calculate_commission_pending(
    mock_session_factory: MagicMock,
) -> None:
    """calculate_commission returns 0 for pending payment."""
    user = _make_user()
    payment = _make_payment(user_id=user.id, status="pending")

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = payment
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await calculate_commission(payment.id)

    assert result["amount"] == 0
    assert result["mentor_id"] is None


@patch("app.bot.services.commission.session_factory")
async def test_calculate_commission_no_mentor(
    mock_session_factory: MagicMock,
) -> None:
    """calculate_commission returns 0 for payment with no mentor."""
    user = _make_user(referred_by_id=None)
    payment = _make_payment(user_id=user.id, status="succeeded")

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    async def side_effect(query):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = payment
        else:
            result.scalar_one_or_none.return_value = user
        return result

    mock_session.execute = AsyncMock(side_effect=side_effect)

    result = await calculate_commission(payment.id)

    assert result["amount"] == 0
    assert result["mentor_id"] is None
