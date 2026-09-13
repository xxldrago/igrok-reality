"""Tests for payment finalize path, paid gates, and pay buttons."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.keyboards.payment import payment_keyboard, staging_payment_keyboard


def _make_user(paid_at=None, started_at=None):
    from app.shared.models.user import User

    return User(
        telegram_id=111,
        first_name="Ivan",
        username="ivan",
        archetype="head",
        xp=0,
        streak=0,
        referral_code="abc123",
        paid_at=paid_at,
        started_at=started_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _session_cm(mock_session):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class TestPaymentKwargs:
    def test_succeed_kwargs_match_model(self) -> None:
        """Payment(...) with succeed_payment kwargs must not raise.

        Regression: paid_at is a User column, not a Payment column.
        """
        from app.shared.models.payment import Payment

        payment = Payment(
            user_id=uuid4(),
            amount=490000,
            currency="RUB",
            status="succeeded",
            idempotency_key="testpay-1",
            platega_transaction_id="test-1",
        )
        assert payment.status == "succeeded"


class TestFinalize:
    @pytest.mark.asyncio
    async def test_finalize_sets_paid_and_starts_clock(self) -> None:
        """First payment: user.paid_at set, started_at reset (no completions)."""
        from app.bot.services import payment_service as ps
        from app.shared.models.payment import Payment

        user = _make_user()
        payment = Payment(user_id=user.id, amount=490000, status="succeeded")

        mock_session = AsyncMock()
        res_user = MagicMock()
        res_user.scalar_one_or_none.return_value = user
        res_cmd = MagicMock()
        res_cmd.scalar_one_or_none.return_value = None  # no completions
        mock_session.execute = AsyncMock(side_effect=[res_user, res_cmd])

        with (
            patch.object(ps, "session_factory", return_value=_session_cm(mock_session)),
            patch.object(ps, "grant_access", new_callable=AsyncMock),
            patch.object(ps, "calculate_commission", new_callable=AsyncMock),
            patch("aiogram.Bot"),
        ):
            with patch.object(
                ps, "get_bot_token", new_callable=AsyncMock, return_value="tok"
            ), patch.object(
                ps, "get_payment_channel_id", new_callable=AsyncMock, return_value=0
            ):
                await ps.finalize_successful_payment(user.id, payment)

        assert user.paid_at is not None
        # Clock reset to ~now (started_at was 2026-01-01)
        assert (datetime.now(timezone.utc) - user.started_at).days < 2
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_finalize_keeps_clock_with_completions(self) -> None:
        """Late payment with existing completions: started_at untouched."""
        from app.bot.services import payment_service as ps
        from app.shared.models.payment import Payment

        started = datetime(2026, 1, 1, tzinfo=timezone.utc)
        user = _make_user(started_at=started)
        payment = Payment(user_id=user.id, amount=490000, status="succeeded")

        mock_session = AsyncMock()
        res_user = MagicMock()
        res_user.scalar_one_or_none.return_value = user
        res_cmd = MagicMock()
        res_cmd.scalar_one_or_none.return_value = uuid4()  # has completions
        mock_session.execute = AsyncMock(side_effect=[res_user, res_cmd])

        with (
            patch.object(ps, "session_factory", return_value=_session_cm(mock_session)),
            patch.object(ps, "grant_access", new_callable=AsyncMock),
            patch.object(ps, "calculate_commission", new_callable=AsyncMock),
            patch("aiogram.Bot"),
        ):
            with patch.object(
                ps, "get_bot_token", new_callable=AsyncMock, return_value="tok"
            ), patch.object(
                ps, "get_payment_channel_id", new_callable=AsyncMock, return_value=0
            ):
                await ps.finalize_successful_payment(user.id, payment)

        assert user.paid_at is not None
        assert user.started_at == started


class TestPaidGates:
    @pytest.mark.asyncio
    async def test_unpaid_command_blocked(self) -> None:
        """Unpaid user gets /pay hint, nothing recorded."""
        from app.bot.handlers import daily as daily_mod

        user = _make_user(paid_at=None)
        message = AsyncMock()
        message.from_user.id = 111
        message.answer = AsyncMock()

        with (
            patch.object(
                daily_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=user
            ),
            patch.object(daily_mod, "_record_command", new_callable=AsyncMock) as mock_record,
        ):
            await daily_mod._handle_scroll_command(message, "/wakeup", "rassvet")

        text = message.answer.call_args[0][0]
        assert "/pay" in text
        mock_record.assert_not_awaited()


class TestPayButtons:
    def test_real_button_is_url(self) -> None:
        kb = payment_keyboard(490000, "https://pay.example/1")
        btn = kb.inline_keyboard[0][0]
        assert btn.url == "https://pay.example/1"
        assert "4900" in btn.text
        assert btn.callback_data is None

    def test_test_button_has_callback(self) -> None:
        kb = staging_payment_keyboard(490000)
        btn = kb.inline_keyboard[0][0]
        assert btn.url is None
        assert btn.callback_data is not None
        assert "4900" in btn.text

    @pytest.mark.asyncio
    async def test_send_pay_prompt_test_mode(self) -> None:
        from app.bot.handlers import payment as pay_mod

        user = _make_user()
        message = AsyncMock()
        message.answer = AsyncMock()
        with (
            patch.object(pay_mod, "get_payments_enabled", new_callable=AsyncMock, return_value=False),
            patch.object(pay_mod, "get_payment_amount", new_callable=AsyncMock, return_value=490000),
        ):
            await pay_mod.send_pay_prompt(message, user)
        text = message.answer.call_args[0][0]
        kwargs = message.answer.call_args[1]
        assert "тестовой оплаты" in text
        btn = kwargs["reply_markup"].inline_keyboard[0][0]
        assert btn.callback_data is not None

    @pytest.mark.asyncio
    async def test_send_pay_prompt_live_mode(self) -> None:
        from app.bot.handlers import payment as pay_mod
        from app.shared.models.payment import Payment

        user = _make_user()
        payment = Payment(user_id=user.id, amount=490000, status="pending")
        message = AsyncMock()
        message.answer = AsyncMock()
        with (
            patch.object(pay_mod, "get_payments_enabled", new_callable=AsyncMock, return_value=True),
            patch.object(pay_mod, "get_payment_amount", new_callable=AsyncMock, return_value=490000),
            patch.object(pay_mod, "create_payment", new_callable=AsyncMock, return_value=payment),
            patch.object(
                pay_mod,
                "call_platega_api",
                new_callable=AsyncMock,
                return_value={"data": {"paymentUrl": "https://pay.example/9"}},
            ),
        ):
            await pay_mod.send_pay_prompt(message, user)
        text = message.answer.call_args[0][0]
        kwargs = message.answer.call_args[1]
        assert "4900" in text
        btn = kwargs["reply_markup"].inline_keyboard[0][0]
        assert btn.url == "https://pay.example/9"
