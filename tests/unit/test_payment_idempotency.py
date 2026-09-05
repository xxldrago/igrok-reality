"""Tests for payment idempotency — duplicate prevention in create_payment."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.payment_service import create_payment, update_payment_status
from app.shared.models.payment import Payment


@pytest.fixture
def user_id() -> uuid4:
    return uuid4()


# --- create_payment idempotency ---


@patch("app.bot.services.payment_service.session_factory")
async def test_create_payment_reuses_pending(
    mock_session_factory: MagicMock, user_id: uuid4
) -> None:
    """create_payment returns existing pending payment when one exists."""
    existing_payment = Payment(
        user_id=user_id,
        amount=4900,
        status="pending",
        idempotency_key="existing-key",
    )
    existing_payment.id = uuid4()

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_payment
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await create_payment(user_id=user_id, amount=4900)

    assert result is existing_payment
    assert result.idempotency_key == "existing-key"
    # No new record created
    mock_session.add.assert_not_called()


@patch("app.bot.services.payment_service.session_factory")
async def test_create_payment_creates_new_when_no_pending(
    mock_session_factory: MagicMock, user_id: uuid4
) -> None:
    """create_payment creates new payment when no pending exists."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # First call (query) returns None — no pending payment
    mock_query_result = MagicMock()
    mock_query_result.scalar_one_or_none.return_value = None

    call_count = 0

    async def side_effect(query):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_query_result  # pending payment check
        # For the new payment insert
        mock_insert_result = MagicMock()
        return mock_insert_result

    mock_session.execute = AsyncMock(side_effect=side_effect)

    def refresh_side_effect(obj):
        obj.id = uuid4()

    mock_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    result = await create_payment(user_id=user_id, amount=4900)

    assert isinstance(result, Payment)
    assert result.status == "pending"
    assert result.idempotency_key is not None
    mock_session.add.assert_called_once()


# --- update_payment_status ---


@patch("app.bot.services.payment_service.session_factory")
async def test_update_payment_status_updates_and_returns(
    mock_session_factory: MagicMock,
) -> None:
    """update_payment_status updates status and returns the payment."""
    payment = Payment(
        user_id=uuid4(),
        amount=4900,
        status="pending",
        idempotency_key="test-key",
    )
    payment.id = uuid4()

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = payment
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await update_payment_status("test-key", "succeeded")

    assert result is payment
    assert payment.status == "succeeded"
    mock_session.commit.assert_awaited_once()


@patch("app.bot.services.payment_service.session_factory")
async def test_update_payment_status_not_found(
    mock_session_factory: MagicMock,
) -> None:
    """update_payment_status returns None when payment not found."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await update_payment_status("nonexistent-key", "succeeded")

    assert result is None
    mock_session.commit.assert_not_awaited()
