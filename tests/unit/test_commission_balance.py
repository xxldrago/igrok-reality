"""Tests for commission balance — one-time logic and balance persistence."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.commission import calculate_commission
from app.shared.models.commission import CommissionBalance
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


def _make_balance(
    *,
    user_id: uuid4 | None = None,
    total_pending: int = 0,
) -> CommissionBalance:
    balance = CommissionBalance(
        user_id=user_id or uuid4(),
        total_pending=total_pending,
    )
    balance.id = uuid4()
    return balance


@patch("app.bot.services.commission.session_factory")
async def test_one_time_commission_first_payment(
    mock_session_factory: MagicMock,
) -> None:
    """calculate_commission returns amount > 0 for first succeeded payment with mentor."""
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
    # Verify balance was persisted
    mock_session.add.assert_called()


@patch("app.bot.services.commission.session_factory")
async def test_one_time_commission_second_payment_no_commission(
    mock_session_factory: MagicMock,
) -> None:
    """calculate_commission returns amount=0 for second succeeded payment (one-time enforcement)."""
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
        else:
            # Payment count query — 2 succeeded payments (not first)
            result.scalar_one.return_value = 2
        return result

    mock_session.execute = AsyncMock(side_effect=side_effect)

    result = await calculate_commission(payment.id)

    assert result["amount"] == 0
    assert result["mentor_id"] is None
    assert result["mentor_telegram_id"] is None
    # Verify balance was NOT persisted
    mock_session.add.assert_not_called()


@patch("app.bot.services.commission.session_factory")
async def test_commission_no_mentor(mock_session_factory: MagicMock) -> None:
    """calculate_commission returns amount=0 when user has no mentor."""
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


@patch("app.bot.services.commission.session_factory")
async def test_balance_created_on_first_commission(
    mock_session_factory: MagicMock,
) -> None:
    """CommissionBalance record is created on first commission with correct total_pending."""
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

    assert result["amount"] == 490
    # Verify a new CommissionBalance was created
    mock_session.add.assert_called()
    added_obj = mock_session.add.call_args[0][0]
    assert isinstance(added_obj, CommissionBalance)
    assert added_obj.user_id == mentor.id
    assert added_obj.total_pending == 490
    assert added_obj.last_commission_at is not None


@patch("app.bot.services.commission.session_factory")
async def test_balance_increments_on_subsequent_commission(
    mock_session_factory: MagicMock,
) -> None:
    """CommissionBalance.total_pending increments on each commission."""
    mentor = _make_user(telegram_id=99999)
    user = _make_user(referred_by_id=mentor.id, telegram_id=11111)
    payment = _make_payment(user_id=user.id, status="succeeded", amount=4900)
    existing_balance = _make_balance(user_id=mentor.id, total_pending=200)

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
            # Balance lookup — existing balance
            result.scalar_one_or_none.return_value = existing_balance
        return result

    mock_session.execute = AsyncMock(side_effect=side_effect)

    result = await calculate_commission(payment.id)

    assert result["amount"] == 490
    # Verify existing balance was incremented
    assert existing_balance.total_pending == 690  # 200 + 490
    assert existing_balance.last_commission_at is not None
    # No new balance added (existing was used)
    mock_session.add.assert_not_called()
