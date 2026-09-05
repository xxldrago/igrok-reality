"""Tests for admin payout — balance query, payout logic, audit trail."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.commission import get_commission_balance, process_payout
from app.shared.models.audit import AuditLog
from app.shared.models.commission import CommissionBalance


def _make_balance(
    *,
    user_id: uuid4 | None = None,
    total_earned: int = 0,
    total_pending: int = 0,
    total_paid_out: int = 0,
) -> CommissionBalance:
    balance = CommissionBalance(
        user_id=user_id or uuid4(),
        total_earned=total_earned,
        total_pending=total_pending,
        total_paid_out=total_paid_out,
    )
    balance.id = uuid4()
    return balance


@pytest.mark.asyncio
@patch("app.bot.services.commission.session_factory")
async def test_process_payout_success(mock_session_factory: MagicMock) -> None:
    """Payout deducts from pending and moves to paid_out."""
    user_id = uuid4()
    balance = _make_balance(user_id=user_id, total_earned=5000, total_pending=5000, total_paid_out=0)

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = balance
    mock_session.execute = AsyncMock(return_value=result_mock)

    result = await process_payout(user_id, 3000)

    assert result["success"] is True
    assert result["amount"] == 3000
    assert balance.total_pending == 2000
    assert balance.total_paid_out == 3000
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("app.bot.services.commission.session_factory")
async def test_process_payout_insufficient(mock_session_factory: MagicMock) -> None:
    """Payout returns error on insufficient balance."""
    user_id = uuid4()
    balance = _make_balance(user_id=user_id, total_pending=1000)

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = balance
    mock_session.execute = AsyncMock(return_value=result_mock)

    result = await process_payout(user_id, 5000)

    assert result["success"] is False
    assert result["error"] == "Insufficient balance"
    assert result["pending"] == 1000
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
@patch("app.bot.services.commission.session_factory")
async def test_process_payout_no_balance(mock_session_factory: MagicMock) -> None:
    """Payout returns error when no balance exists."""
    user_id = uuid4()

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=result_mock)

    result = await process_payout(user_id, 1000)

    assert result["success"] is False
    assert result["error"] == "No commission balance found"


@pytest.mark.asyncio
@patch("app.bot.services.commission.session_factory")
async def test_process_payout_audit_log(mock_session_factory: MagicMock) -> None:
    """Payout creates AuditLog entry with correct action and details."""
    user_id = uuid4()
    admin_id = uuid4()
    balance = _make_balance(user_id=user_id, total_pending=5000)

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = balance
    mock_session.execute = AsyncMock(return_value=result_mock)

    await process_payout(user_id, 1000, admin_id=admin_id)

    mock_session.add.assert_called_once()
    audit_entry = mock_session.add.call_args[0][0]
    assert isinstance(audit_entry, AuditLog)
    assert audit_entry.admin_id == admin_id
    assert audit_entry.action == "commission_payout"
    assert f"user_id={user_id}" in audit_entry.details
    assert "amount=1000" in audit_entry.details


@pytest.mark.asyncio
@patch("app.bot.services.commission.session_factory")
async def test_get_commission_balance_found(mock_session_factory: MagicMock) -> None:
    """get_commission_balance returns balance data when exists."""
    user_id = uuid4()
    balance = _make_balance(
        user_id=user_id,
        total_earned=10000,
        total_pending=7000,
        total_paid_out=3000,
    )

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = balance
    mock_session.execute = AsyncMock(return_value=result_mock)

    result = await get_commission_balance(user_id)

    assert result is not None
    assert result["total_earned"] == 10000
    assert result["total_pending"] == 7000
    assert result["total_paid_out"] == 3000


@pytest.mark.asyncio
@patch("app.bot.services.commission.session_factory")
async def test_get_commission_balance_not_found(mock_session_factory: MagicMock) -> None:
    """get_commission_balance returns None when no balance."""
    user_id = uuid4()

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=result_mock)

    result = await get_commission_balance(user_id)

    assert result is None
