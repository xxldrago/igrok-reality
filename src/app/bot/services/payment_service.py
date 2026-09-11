"""Payment service — Platega.io API client and payment CRUD."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select

logger = logging.getLogger(__name__)

from app.shared.database import session_factory
from app.shared.models.payment import Payment
from app.shared.models.user import User
from app.bot.services.settings_service import (
    get_bot_username,
    get_bot_token,
    get_platega_credentials,
    get_payment_channel_id,
)
from app.bot.services.channel_access import grant_access, revoke_access
from app.bot.services.commission import calculate_commission


async def create_payment(user_id: UUID, amount: int, currency: str = "RUB") -> Payment:
    """Create a pending payment record with a unique idempotency key.

    If a pending payment already exists for this user, reuses it instead
    of creating a duplicate — prevents duplicate charges when the user
    taps /pay multiple times.
    """
    # Idempotency: return existing pending payment if one exists
    async with session_factory() as session:
        result = await session.execute(
            select(Payment).where(
                Payment.user_id == user_id,
                Payment.status == "pending",
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

    # No pending payment — create a new one
    idempotency_key = str(uuid.uuid4())

    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency=currency,
        status="pending",
        idempotency_key=idempotency_key,
    )

    async with session_factory() as session:
        session.add(payment)
        await session.commit()
        await session.refresh(payment)

    return payment


async def update_payment_status(idempotency_key: str, status: str) -> Payment | None:
    """Update payment status by idempotency key.

    Looks up the payment, sets the new status, commits, and returns
    the updated payment. Returns None if no payment found.
    """
    async with session_factory() as session:
        result = await session.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            return None
        payment.status = status
        await session.commit()
        return payment


async def get_payment(idempotency_key: str) -> Payment | None:
    """Look up a payment by its idempotency key."""
    async with session_factory() as session:
        result = await session.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()


async def record_test_payment(user_id: UUID, amount: int) -> Payment:
    """Create a succeeded payment record for staging (payments_enabled=false).

    Emulates a successful Platega payment end-to-end: writes record, grants
    channel access, notifies the payment channel, and calculates commission —
    exactly as the real webhook `succeeded` path does, but without an external
    redirect.
    """
    return await succeed_payment(
        user_id=user_id,
        amount=amount,
        order_id=f"testpay-{uuid.uuid4()}",
        transaction_id=f"test-{uuid.uuid4()}",
    )


async def succeed_payment(
    user_id: UUID, amount: int, order_id: str, transaction_id: str | None = None
) -> Payment:
    """Execute the full sucsess path (shared by webhook + test payment).

    - Inserts a succeeded Payment row.
    - Grants channel access (if configured).
    - Notifies the user via Telegram.
    - Posts to the payment channel (if configured).
    - Calculates mentor commission.
    """
    from aiogram import Bot

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"succeed_payment: user {user_id} not found")

        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency="RUB",
            status="succeeded",
            idempotency_key=order_id,
            platega_transaction_id=transaction_id,
            paid_at=datetime.now(timezone.utc),
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)

    # Channel access + notifications (best-effort, never breaks the payment)
    try:
        bot = Bot(token=await get_bot_token())
        try:
            await grant_access(user.id, bot)
            await bot.send_message(
                chat_id=user.telegram_id,
                text="Оплата прошла успешно! Доступ в квест открыт.",
            )
            await _notify_payment_channel_bot(bot, amount, order_id, user)
        finally:
            await bot.session.close()
    except Exception:
        logger.exception("succeed_payment: notification failed for user %s", user_id)

    # Mentor commission (best-effort)
    try:
        await calculate_commission(user_id, payment.id)
    except Exception:
        logger.exception("succeed_payment: commission failed for user %s", user_id)

    return payment


async def _notify_payment_channel_bot(bot: Bot, amount: int, order_id: str, user: "User") -> None:
    """Post a payment-success line to the payment channel (best-effort)."""
    try:
        channel_id = await get_payment_channel_id()
        if not channel_id:
            return
        label = f"@{user.username}" if user.username else user.first_name
        await bot.send_message(
            chat_id=channel_id,
            text=f"✅ Оплата {amount // 100}₽ — {label} (tg {user.telegram_id})\nЗаказ {order_id}",
        )
    except Exception:
        logger.exception("Failed to notify payment channel")


async def call_platega_api(payment: Payment) -> dict:
    """Call Platega.io API to initiate a payment transaction.

    Updates payment.platega_transaction_id from the response.
    Returns the full response JSON.
    """
    merchant_id, secret = await get_platega_credentials()
    bot_username = await get_bot_username()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.platega.io/v2/transaction/process",
            headers={
                "X-MerchantId": merchant_id,
                "X-Secret": secret,
            },
            json={
                "paymentMethod": 3,
                "paymentDetails": {"amount": payment.amount, "currency": payment.currency},
                "return": f"https://t.me/{bot_username}?start=payment_success",
                "failedUrl": f"https://t.me/{bot_username}?start=payment_failed",
                "payload": str(payment.user_id),
                "orderId": payment.idempotency_key,
                "metadata": {"user_id": str(payment.user_id)},
            },
        )
        data = response.json()

    # Update payment with Platega transaction ID
    platega_id = data.get("data", {}).get("paymentId")
    if platega_id:
        async with session_factory() as session:
            result = await session.execute(
                select(Payment).where(Payment.id == payment.id)
            )
            db_payment = result.scalar_one()
            db_payment.platega_transaction_id = platega_id
            await session.commit()

    return data
