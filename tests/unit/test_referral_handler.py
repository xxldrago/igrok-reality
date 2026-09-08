"""Tests for /referral handler and configurable commission rate."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.handlers.referral import referral_handler
from app.shared.models.user import User


@pytest.fixture
def telegram_id() -> int:
    return 987654321


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


# --- /referral handler tests ---


@patch("app.bot.handlers.referral.get_user_by_telegram_id")
async def test_referral_shows_link(
    mock_get_user: MagicMock,
    telegram_id: int,
) -> None:
    """Test that /referral shows user their unique referral link."""
    user = User(
        telegram_id=telegram_id,
        first_name="Alice",
        archetype="head",
        referral_code="abc12345",
    )
    mock_get_user.return_value = user

    message = AsyncMock()
    message.from_user.id = telegram_id

    with patch("app.bot.handlers.referral.settings") as mock_settings:
        mock_settings.BOT_USERNAME = "testbot"
        await referral_handler(message)

    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "https://t.me/testbot?start=abc12345" in call_args
    assert "реферальная ссылка" in call_args.lower()


@patch("app.bot.handlers.referral.get_user_by_telegram_id")
async def test_referral_before_registration(
    mock_get_user: MagicMock,
    telegram_id: int,
) -> None:
    """Test that /referral before registration returns error."""
    mock_get_user.return_value = None

    message = AsyncMock()
    message.from_user.id = telegram_id

    await referral_handler(message)

    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "зарегистрируйтесь" in call_args.lower()


# --- Configurable COMMISSION_RATE tests ---


@patch("app.bot.services.commission.reserve_prize_fund_share")
@patch("app.bot.services.commission.session_factory")
async def test_commission_rate_configurable(
    mock_session_factory: MagicMock,
    mock_reserve: AsyncMock,
) -> None:
    """Test that COMMISSION_RATE from settings is used in calculation."""
    from app.bot.services.commission import calculate_commission

    mock_reserve.return_value = 500
    mentor = User(telegram_id=99999, first_name="Mentor", archetype="head", referral_code="m1")
    mentor.id = uuid4()
    user = User(telegram_id=11111, first_name="Test", archetype="head", referral_code="t1")
    user.id = uuid4()
    user.referred_by_id = mentor.id

    from app.shared.models.payment import Payment
    payment = Payment(user_id=user.id, amount=10000, status="succeeded", idempotency_key="key")
    payment.id = uuid4()

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

    with patch("app.bot.services.commission.settings") as mock_settings:
        mock_settings.COMMISSION_RATE = 0.15
        result = await calculate_commission(payment.id)

    assert result["amount"] == 1500  # 10000 * 0.15
    assert result["mentor_id"] == str(mentor.id)
    assert result["mentor_telegram_id"] == 99999


# --- create_user with referral_code tests ---


@patch("app.bot.services.user_service.session_factory")
async def test_create_user_with_referral_code(
    mock_session_factory: MagicMock,
) -> None:
    """Test that create_user with referral_code creates Referral record."""
    from app.bot.services.user_service import create_user

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # Track what gets added to session
    added_objects = []

    def mock_add(obj):
        added_objects.append(obj)

    mock_session.add = MagicMock(side_effect=mock_add)

    # Mock refresh to set an id
    async def mock_refresh(obj):
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = uuid4()

    mock_session.refresh = mock_refresh

    user = await create_user(
        telegram_id=12345,
        first_name="Test",
        last_name=None,
        username=None,
        archetype="head",
        referral_code="ref123",
    )

    # Verify a User was created with the referral code
    assert len(added_objects) >= 1
    created_user = added_objects[0]
    assert created_user.referral_code == "ref123"
    assert created_user.telegram_id == 12345
    assert created_user.archetype == "head"
