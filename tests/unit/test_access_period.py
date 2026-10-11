"""Tests for 30-day access periods — helpers, finalize extension, renewal reminders."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.shared.models.user import User


def _user(**kwargs) -> User:
    now = datetime.now(timezone.utc)
    return User(
        telegram_id=kwargs.get("telegram_id", 777),
        first_name="Test",
        paid_at=kwargs.get("paid_at", now - timedelta(days=1)),
        access_until=kwargs.get("access_until", now + timedelta(days=5)),
    )


class TestAccessHelpers:
    def test_active(self) -> None:
        from app.bot.services.user_service import is_access_active

        assert is_access_active(_user()) is True

    def test_expired(self) -> None:
        from app.bot.services.user_service import is_access_active

        assert (
            is_access_active(
                _user(access_until=datetime.now(timezone.utc) - timedelta(hours=1))
            )
            is False
        )

    def test_never_paid(self) -> None:
        from app.bot.services.user_service import is_access_active

        assert is_access_active(_user(paid_at=None, access_until=None)) is False

    def test_days_until_expiry(self) -> None:
        from app.bot.services.user_service import days_until_expiry

        assert days_until_expiry(_user(access_until=datetime.now(timezone.utc) + timedelta(days=3))) == 3
        assert days_until_expiry(_user(paid_at=None, access_until=None)) is None

    def test_gate_messages(self) -> None:
        from app.bot.services.user_service import access_gate_message

        assert access_gate_message(None) == "Сначала оплатите участие: /pay"
        assert access_gate_message(_user(paid_at=None, access_until=None)).startswith("Сначала")
        expired = _user(access_until=datetime.now(timezone.utc) - timedelta(days=1))
        assert "завершён" in access_gate_message(expired)
        assert access_gate_message(_user()) is None

    def test_grant_first_time(self) -> None:
        from app.bot.services.user_service import ACCESS_PERIOD_DAYS, grant_access_period

        user = _user(paid_at=None, access_until=None)
        now = datetime.now(timezone.utc)
        grant_access_period(user, now)
        assert user.access_until == now + timedelta(days=ACCESS_PERIOD_DAYS)

    def test_grant_early_renewal_stacks(self) -> None:
        from app.bot.services.user_service import grant_access_period

        now = datetime.now(timezone.utc)
        user = _user(access_until=now + timedelta(days=2))
        grant_access_period(user, now)
        assert user.access_until == now + timedelta(days=32)

    def test_grant_late_renewal_restarts(self) -> None:
        from app.bot.services.user_service import grant_access_period

        now = datetime.now(timezone.utc)
        user = _user(access_until=now - timedelta(days=5))
        grant_access_period(user, now)
        assert user.access_until == now + timedelta(days=30)


class TestFinalizeExtendsAccess:
    @pytest.mark.asyncio
    async def test_finalize_sets_access_until(self) -> None:
        from app.bot.services import payment_service as ps
        from app.shared.models.payment import Payment

        user = _user(paid_at=None, access_until=None)
        payment = Payment(user_id=user.id, amount=100, status="succeeded")

        mock_session = AsyncMock()
        res_user = MagicMock()
        res_user.scalar_one_or_none.return_value = user
        mock_session.execute = AsyncMock(return_value=res_user)

        with (
            patch.object(ps, "session_factory") as mock_factory,
            patch.object(ps, "grant_access", new_callable=AsyncMock),
            patch.object(ps, "calculate_commission", new_callable=AsyncMock),
            patch("aiogram.Bot"),
            patch(
                "app.bot.services.quest_group_service.assign_user_to_group",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(ps, "get_bot_token", new_callable=AsyncMock, return_value="tok"),
            patch.object(ps, "get_payment_channel_id", new_callable=AsyncMock, return_value=0),
        ):
            cm = AsyncMock()
            cm.__aenter__ = AsyncMock(return_value=mock_session)
            cm.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = cm
            await ps.finalize_successful_payment(user.id, payment)

        assert user.paid_at is not None
        assert user.access_until is not None
        assert user.access_until > datetime.now(timezone.utc)


def _session_cm(mock_session):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class TestRenewalReminders:
    def _run_task(self, users):
        from app.worker.tasks import notifications as notif_mod

        res = MagicMock()
        res.scalars.return_value.all.return_value = users
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=res)

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        return notif_mod, mock_session, mock_bot

    @pytest.mark.asyncio
    async def test_reminders_and_expiry_notice(self) -> None:
        from app.worker.tasks import notifications as notif_mod

        now = datetime.now(timezone.utc)
        users = [
            _user(telegram_id=1, access_until=now + timedelta(days=3)),
            _user(telegram_id=2, access_until=now + timedelta(days=2)),
            _user(telegram_id=3, access_until=now + timedelta(days=1)),
            _user(telegram_id=4, access_until=now + timedelta(hours=12)),  # expiry day
            _user(telegram_id=5, access_until=now + timedelta(days=10)),  # skip
            _user(telegram_id=6, access_until=now - timedelta(days=2)),  # already notified
            _user(telegram_id=7, paid_at=None, access_until=None),  # never paid
        ]
        res = MagicMock()
        res.scalars.return_value.all.return_value = users
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=res)
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()
        mock_bot.session.close = AsyncMock()

        with (
            patch.object(notif_mod, "session_factory", return_value=_session_cm(mock_session)),
            patch.object(notif_mod, "get_bot_token", new_callable=AsyncMock, return_value="tok"),
            patch.object(notif_mod, "Bot", return_value=mock_bot),
        ):
            await notif_mod.subscription_renewal_reminders({})

        sent_to = {c[0][0] for c in mock_bot.send_message.call_args_list}
        assert sent_to == {1, 2, 3, 4}
        # every message carries the pay button
        for c in mock_bot.send_message.call_args_list:
            assert c[1]["reply_markup"] is not None
        texts = {c[0][0]: c[0][1] for c in mock_bot.send_message.call_args_list}
        assert "через 3 дня" in texts[1]
        assert "через 2 дня" in texts[2]
        assert "через 1 день" in texts[3]
        assert "завершён" in texts[4]
