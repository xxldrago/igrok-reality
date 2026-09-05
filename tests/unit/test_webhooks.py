"""Tests for webhooks — header verification, status routing, idempotency."""

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

# Patch settings before importing webhook module
with patch("app.shared.config.settings") as _mock_settings:
    _mock_settings.PLATEGA_MERCHANT_ID = "test-merchant"
    _mock_settings.PLATEGA_SECRET = "test-secret"
    _mock_settings.BOT_TOKEN = "test-token"
    from app.api.webhooks import router as _webhook_router  # noqa: F401

VALID_HEADERS = {"X-MerchantId": "test-merchant", "X-Secret": "test-secret"}


def _make_payment(
    *,
    user_id: uuid4 | None = None,
    status: str = "pending",
    idempotency_key: str = "order-123",
) -> Payment:
    """Create a Payment object for testing."""
    return Payment(
        user_id=user_id or uuid4(),
        amount=4900,
        status=status,
        idempotency_key=idempotency_key,
    )


def _make_user(*, telegram_id: int = 99999) -> User:
    """Create a User object for testing."""
    return User(
        telegram_id=telegram_id,
        first_name="Test",
        username="testuser",
    )


# --- Header verification ---


@pytest.mark.asyncio
@patch("app.api.webhooks.settings")
async def test_webhook_invalid_merchant_id(mock_settings: MagicMock) -> None:
    """Request with invalid X-MerchantId returns 403-like error."""
    mock_settings.PLATEGA_MERCHANT_ID = "correct-merchant"
    mock_settings.PLATEGA_SECRET = "correct-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhook/platega",
            headers={"X-MerchantId": "wrong-merchant", "X-Secret": "correct-secret"},
            json={"orderId": "order-1", "status": "CONFIRMED"},
        )

    assert response.status_code == 200
    assert response.json() == {"error": "invalid credentials"}


@pytest.mark.asyncio
@patch("app.api.webhooks.settings")
async def test_webhook_invalid_secret(mock_settings: MagicMock) -> None:
    """Request with invalid X-Secret returns error."""
    mock_settings.PLATEGA_MERCHANT_ID = "correct-merchant"
    mock_settings.PLATEGA_SECRET = "correct-secret"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhook/platega",
            headers={"X-MerchantId": "correct-merchant", "X-Secret": "wrong-secret"},
            json={"orderId": "order-1", "status": "CONFIRMED"},
        )

    assert response.status_code == 200
    assert response.json() == {"error": "invalid credentials"}


# --- Status routing ---


@pytest.mark.asyncio
@patch("app.api.webhooks.calculate_commission", new_callable=AsyncMock)
@patch("app.api.webhooks._send_payment_notification", new_callable=AsyncMock)
@patch("app.api.webhooks.grant_access", new_callable=AsyncMock)
@patch("app.api.webhooks.Bot")
@patch("app.api.webhooks.session_factory")
@patch("app.api.webhooks.get_payment", new_callable=AsyncMock)
@patch("app.api.webhooks.settings")
async def test_webhook_confirmed(
    mock_settings: MagicMock,
    mock_get_payment: AsyncMock,
    mock_session_factory: MagicMock,
    mock_bot_cls: MagicMock,
    mock_grant_access: AsyncMock,
    mock_notify: AsyncMock,
    mock_calculate_commission: AsyncMock,
) -> None:
    """CONFIRMED status updates payment to 'succeeded' and sends success message."""
    mock_settings.PLATEGA_MERCHANT_ID = "test-merchant"
    mock_settings.PLATEGA_SECRET = "test-secret"

    payment = _make_payment(status="pending")
    mock_get_payment.return_value = payment

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # Mock the execute chain for payment lookup
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = payment
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock the execute chain for user lookup
    user = _make_user()
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user

    call_count = 0

    async def side_effect(query):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_result  # payment query
        return mock_user_result  # user query

    mock_session.execute = AsyncMock(side_effect=side_effect)

    # Commission returns no mentor (no commission notification)
    mock_calculate_commission.return_value = {
        "amount": 0,
        "mentor_id": None,
        "mentor_telegram_id": None,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhook/platega",
            headers=VALID_HEADERS,
            json={
                "orderId": "order-123",
                "status": "CONFIRMED",
                "transactionId": "tx-456",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert payment.status == "succeeded"
    assert payment.platega_transaction_id == "tx-456"
    mock_grant_access.assert_awaited_once()
    mock_notify.assert_awaited_once_with(
        99999, "Оплата прошла успешно! Доступ в канал открыт."
    )
    mock_calculate_commission.assert_awaited_once_with(payment.id)


@pytest.mark.asyncio
@patch("app.api.webhooks._send_payment_notification", new_callable=AsyncMock)
@patch("app.api.webhooks.Bot")
@patch("app.api.webhooks.session_factory")
@patch("app.api.webhooks.get_payment", new_callable=AsyncMock)
@patch("app.api.webhooks.settings")
async def test_webhook_canceled(
    mock_settings: MagicMock,
    mock_get_payment: AsyncMock,
    mock_session_factory: MagicMock,
    mock_bot_cls: MagicMock,
    mock_notify: AsyncMock,
) -> None:
    """CANCELED status updates payment to 'canceled' and sends cancel message."""
    mock_settings.PLATEGA_MERCHANT_ID = "test-merchant"
    mock_settings.PLATEGA_SECRET = "test-secret"

    payment = _make_payment(status="pending")
    mock_get_payment.return_value = payment

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    user = _make_user()
    mock_payment_result = MagicMock()
    mock_payment_result.scalar_one.return_value = payment
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user

    call_count = 0

    async def side_effect(query):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_payment_result
        return mock_user_result

    mock_session.execute = AsyncMock(side_effect=side_effect)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhook/platega",
            headers=VALID_HEADERS,
            json={"orderId": "order-123", "status": "CANCELED"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert payment.status == "canceled"
    mock_notify.assert_awaited_once_with(
        99999, "Оплата отменена. Вы можете попробовать снова."
    )


@pytest.mark.asyncio
@patch("app.api.webhooks._send_payment_notification", new_callable=AsyncMock)
@patch("app.api.webhooks.revoke_access", new_callable=AsyncMock)
@patch("app.api.webhooks.Bot")
@patch("app.api.webhooks.session_factory")
@patch("app.api.webhooks.get_payment", new_callable=AsyncMock)
@patch("app.api.webhooks.settings")
async def test_webhook_chargebacked(
    mock_settings: MagicMock,
    mock_get_payment: AsyncMock,
    mock_session_factory: MagicMock,
    mock_bot_cls: MagicMock,
    mock_revoke_access: AsyncMock,
    mock_notify: AsyncMock,
) -> None:
    """CHARGEBACKED status updates payment to 'chargebacked' and sends revoke message."""
    mock_settings.PLATEGA_MERCHANT_ID = "test-merchant"
    mock_settings.PLATEGA_SECRET = "test-secret"

    payment = _make_payment(status="succeeded")
    mock_get_payment.return_value = payment

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    user = _make_user()
    mock_payment_result = MagicMock()
    mock_payment_result.scalar_one.return_value = payment
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user

    call_count = 0

    async def side_effect(query):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_payment_result
        return mock_user_result

    mock_session.execute = AsyncMock(side_effect=side_effect)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhook/platega",
            headers=VALID_HEADERS,
            json={"orderId": "order-123", "status": "CHARGEBACKED"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert payment.status == "chargebacked"
    mock_revoke_access.assert_awaited_once()
    mock_notify.assert_awaited_once_with(
        99999, "Возврат оформлен. Доступ в канал закрыт."
    )


# --- Idempotency ---


@pytest.mark.asyncio
@patch("app.api.webhooks.get_payment", new_callable=AsyncMock)
@patch("app.api.webhooks.settings")
async def test_webhook_unknown_order(
    mock_settings: MagicMock,
    mock_get_payment: AsyncMock,
) -> None:
    """Unknown orderId returns 200 OK without crash."""
    mock_settings.PLATEGA_MERCHANT_ID = "test-merchant"
    mock_settings.PLATEGA_SECRET = "test-secret"
    mock_get_payment.return_value = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhook/platega",
            headers=VALID_HEADERS,
            json={"orderId": "unknown-order", "status": "CONFIRMED"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
@patch("app.api.webhooks._send_payment_notification", new_callable=AsyncMock)
@patch("app.api.webhooks.session_factory")
@patch("app.api.webhooks.get_payment", new_callable=AsyncMock)
@patch("app.api.webhooks.settings")
async def test_webhook_duplicate_idempotent(
    mock_settings: MagicMock,
    mock_get_payment: AsyncMock,
    mock_session_factory: MagicMock,
    mock_notify: AsyncMock,
) -> None:
    """Duplicate webhook for same orderId is handled gracefully."""
    mock_settings.PLATEGA_MERCHANT_ID = "test-merchant"
    mock_settings.PLATEGA_SECRET = "test-secret"

    # First webhook: pending -> succeeded (valid)
    payment = _make_payment(status="succeeded")
    mock_get_payment.return_value = payment

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = payment
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Second webhook: same status (already succeeded) — invalid transition, should be idempotent
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First call
        response1 = await client.post(
            "/webhook/platega",
            headers=VALID_HEADERS,
            json={"orderId": "order-123", "status": "CONFIRMED"},
        )
        # Duplicate call
        response2 = await client.post(
            "/webhook/platega",
            headers=VALID_HEADERS,
            json={"orderId": "order-123", "status": "CONFIRMED"},
        )

    assert response1.status_code == 200
    assert response2.status_code == 200
    # Both return OK — idempotent
    assert response1.json() == {"status": "ok"}
    assert response2.json() == {"status": "ok"}
