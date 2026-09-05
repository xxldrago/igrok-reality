"""Tests for payment_service — create_payment, idempotency key generation, get_payment."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.payment_service import create_payment, get_payment
from app.shared.models.payment import Payment


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


# --- create_payment ---


@patch("app.bot.services.payment_service.session_factory")
async def test_create_payment(
    mock_session_factory: MagicMock, user_id: UUID
) -> None:
    """create_payment returns Payment with status='pending' and idempotency_key set."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # Make refresh capture the payment so it has an id
    def refresh_side_effect(obj):
        obj.id = uuid4()

    mock_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    payment = await create_payment(user_id=user_id, amount=4900)

    assert isinstance(payment, Payment)
    assert payment.status == "pending"
    assert payment.idempotency_key is not None
    assert payment.user_id == user_id
    assert payment.amount == 4900
    assert payment.currency == "RUB"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


@patch("app.bot.services.payment_service.session_factory")
async def test_create_payment_idempotency_key_unique(
    mock_session_factory: MagicMock,
) -> None:
    """Two create_payment calls produce different idempotency keys."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    def refresh_side_effect(obj):
        obj.id = uuid4()

    mock_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    payment1 = await create_payment(user_id=uuid4(), amount=4900)
    payment2 = await create_payment(user_id=uuid4(), amount=4900)

    assert payment1.idempotency_key != payment2.idempotency_key


# --- get_payment ---


@patch("app.bot.services.payment_service.session_factory")
async def test_get_payment_found(mock_session_factory: MagicMock) -> None:
    """get_payment returns Payment when idempotency_key exists."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    expected = Payment(
        user_id=uuid4(),
        amount=4900,
        status="pending",
        idempotency_key="test-key-123",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await get_payment("test-key-123")

    assert result is expected


@patch("app.bot.services.payment_service.session_factory")
async def test_get_payment_not_found(mock_session_factory: MagicMock) -> None:
    """get_payment returns None when idempotency_key not found."""
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await get_payment("nonexistent-key")

    assert result is None
