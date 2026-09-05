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


def _make_context_manager_factory(*sessions: AsyncMock) -> MagicMock:
    """Return a mock session_factory that yields different sessions per call."""
    factory = MagicMock()
    idx = 0

    async def _aenter(_self):
        nonlocal idx
        session = sessions[idx]
        idx += 1
        return session

    async def _aexit(_self, *args):
        return False

    factory.return_value.__aenter__ = _aenter
    factory.return_value.__aexit__ = _aexit
    return factory


@patch("app.bot.services.payment_service.session_factory")
async def test_create_payment(
    mock_session_factory: MagicMock, user_id: UUID
) -> None:
    """create_payment returns Payment with status='pending' and idempotency_key set."""
    # First session: idempotency query returns None (no pending payment)
    query_session = AsyncMock()
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = None
    query_session.execute = AsyncMock(return_value=query_result)

    # Second session: insert new payment
    insert_session = AsyncMock()
    insert_session.add = MagicMock()

    def refresh_side_effect(obj):
        obj.id = uuid4()

    insert_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    mock_session_factory.return_value.__aenter__ = AsyncMock(
        side_effect=[query_session, insert_session]
    )
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    payment = await create_payment(user_id=user_id, amount=4900)

    assert isinstance(payment, Payment)
    assert payment.status == "pending"
    assert payment.idempotency_key is not None
    assert payment.user_id == user_id
    assert payment.amount == 4900
    assert payment.currency == "RUB"
    insert_session.add.assert_called_once()
    insert_session.commit.assert_awaited_once()


@patch("app.bot.services.payment_service.session_factory")
async def test_create_payment_idempotency_key_unique(
    mock_session_factory: MagicMock,
) -> None:
    """Two create_payment calls produce different idempotency keys."""
    call_count = 0

    def make_session():
        nonlocal call_count
        call_count += 1
        session = AsyncMock()
        session.add = MagicMock()

        def refresh_side_effect(obj):
            obj.id = uuid4()

        session.refresh = AsyncMock(side_effect=refresh_side_effect)
        # Each call to create_payment opens 2 sessions: query + insert
        return session

    sessions = []
    for _ in range(4):
        sessions.append(make_session())

    mock_session_factory.return_value.__aenter__ = AsyncMock(
        side_effect=sessions
    )
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # Make all query sessions return None (no pending payment)
    for s in sessions[::2]:
        query_result = MagicMock()
        query_result.scalar_one_or_none.return_value = None
        s.execute = AsyncMock(return_value=query_result)

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
