"""Tests for YooKassa provider — API client and webhook verification."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.api.main import app
from app.shared.models.payment import Payment
from app.shared.models.user import User


def _make_payment(**kwargs) -> Payment:
    return Payment(
        user_id=kwargs.get("user_id") or uuid4(),
        amount=kwargs.get("amount", 490000),
        currency="RUB",
        status=kwargs.get("status", "pending"),
        idempotency_key=kwargs.get("idempotency_key", "order-yk-1"),
    )


def _session_cm(mock_session):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class TestAmountFormat:
    def test_kopecks_to_rub(self) -> None:
        from app.bot.services.payment_service import _kopecks_to_rub

        assert _kopecks_to_rub(490000) == "4900.00"
        assert _kopecks_to_rub(1) == "0.01"


class TestCreateYookassaPayment:
    @pytest.mark.asyncio
    async def test_creates_and_returns_confirmation_url(self) -> None:
        from app.bot.services import payment_service as svc

        payment = _make_payment()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "id": "yk-123",
            "confirmation": {"confirmation_url": "https://yookassa.example/confirm"},
        }
        mock_post = AsyncMock(return_value=mock_resp)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post

        mock_session = AsyncMock()
        row = MagicMock()
        res = MagicMock()
        res.scalar_one.return_value = row
        mock_session.execute = AsyncMock(return_value=res)

        with (
            patch.object(svc, "get_yookassa_credentials", new_callable=AsyncMock, return_value=("shop", "key")),
            patch.object(svc, "get_yookassa_return_url", new_callable=AsyncMock, return_value="https://t.me/bot"),
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.object(svc, "session_factory", return_value=_session_cm(mock_session)),
        ):
            url = await svc.create_yookassa_payment(payment)

        assert url == "https://yookassa.example/confirm"
        assert row.yookassa_payment_id == "yk-123"
        body = mock_post.call_args[1]["json"]
        assert body["amount"] == {"value": "4900.00", "currency": "RUB"}
        assert body["capture"] is True
        assert body["confirmation"]["return_url"] == "https://t.me/bot"

    @pytest.mark.asyncio
    async def test_missing_credentials(self) -> None:
        from app.bot.services import payment_service as svc

        with patch.object(
            svc, "get_yookassa_credentials", new_callable=AsyncMock, return_value=("", "")
        ):
            with pytest.raises(RuntimeError):
                await svc.create_yookassa_payment(_make_payment())

    @pytest.mark.asyncio
    async def test_bad_response(self) -> None:
        from app.bot.services import payment_service as svc

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"type": "error"}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with (
            patch.object(svc, "get_yookassa_credentials", new_callable=AsyncMock, return_value=("shop", "key")),
            patch.object(svc, "get_yookassa_return_url", new_callable=AsyncMock, return_value="https://t.me/bot"),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            with pytest.raises(ValueError):
                await svc.create_yookassa_payment(_make_payment())


class TestYookassaWebhook:
    def _notify(self, yk_id="yk-123"):
        return {"event": "payment.succeeded", "object": {"id": yk_id, "status": "succeeded"}}

    @pytest.mark.asyncio
    @patch("app.api.webhooks.finalize_successful_payment", new_callable=AsyncMock)
    @patch("app.api.webhooks.session_factory")
    @patch("app.api.webhooks.get_yookassa_payment", new_callable=AsyncMock)
    async def test_succeeded_finalizes(
        self, mock_remote: AsyncMock, mock_factory: MagicMock, mock_finalize: AsyncMock
    ) -> None:
        mock_remote.return_value = {"id": "yk-123", "status": "succeeded"}
        payment = _make_payment(status="pending")
        user = User(telegram_id=99999, first_name="Test")

        res_pay = MagicMock()
        res_pay.scalar_one_or_none.return_value = payment
        res_row = MagicMock()
        res_row.scalar_one.return_value = payment
        res_user = MagicMock()
        res_user.scalar_one_or_none.return_value = user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[res_pay, res_row, res_user])
        mock_factory.return_value = _session_cm(mock_session)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/webhook/yookassa", json=self._notify())

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert payment.status == "succeeded"
        mock_finalize.assert_awaited_once_with(user.id, payment)

    @pytest.mark.asyncio
    @patch("app.api.webhooks.finalize_successful_payment", new_callable=AsyncMock)
    @patch("app.api.webhooks.get_yookassa_payment", new_callable=AsyncMock)
    async def test_notification_not_trusted_replay_is_noop(
        self, mock_remote: AsyncMock, mock_finalize: AsyncMock
    ) -> None:
        """Replay for an already-succeeded payment: invalid transition, no finalize."""
        mock_remote.return_value = {"id": "yk-123", "status": "succeeded"}
        payment = _make_payment(status="succeeded")

        res_pay = MagicMock()
        res_pay.scalar_one_or_none.return_value = payment
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=res_pay)

        with patch("app.api.webhooks.session_factory", return_value=_session_cm(mock_session)):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/webhook/yookassa", json=self._notify())

        assert response.json() == {"status": "ok"}
        mock_finalize.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.api.webhooks.get_yookassa_payment", new_callable=AsyncMock)
    async def test_unknown_payment_ok(self, mock_remote: AsyncMock) -> None:
        mock_remote.return_value = {"id": "yk-999", "status": "succeeded"}
        res_pay = MagicMock()
        res_pay.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=res_pay)

        with patch("app.api.webhooks.session_factory", return_value=_session_cm(mock_session)):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/webhook/yookassa",
                    json={"event": "payment.succeeded", "object": {"id": "yk-999"}},
                )

        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_missing_object_id_ok(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/webhook/yookassa", json={"object": {}})

        assert response.json() == {"status": "ok"}
