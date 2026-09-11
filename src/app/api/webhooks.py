"""Platega.io webhook endpoint — payment status routing and user notifications."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Bot
from fastapi import APIRouter, Request, status
from sqlalchemy import select

from app.bot.services.channel_access import grant_access, revoke_access
from app.bot.services.commission import calculate_commission
from app.bot.services.payment_service import get_payment
from app.bot.services.settings_service import get_bot_token, get_platega_credentials
from app.shared.database import session_factory
from app.shared.models.payment import Payment
from app.shared.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Valid payment status transitions (T-05-05 mitigation)
VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["succeeded", "canceled"],
    "succeeded": ["chargebacked", "refunded"],
}


def _is_valid_transition(current: str, target: str) -> bool:
    """Check if a payment status transition is allowed."""
    allowed = VALID_TRANSITIONS.get(current, [])
    return target in allowed


async def _send_payment_notification(user_telegram_id: int, text: str) -> None:
    """Send a notification message to a user via Telegram Bot.

    Catches and logs failures (e.g. user blocked bot) without crashing.
    """
    try:
        bot = Bot(token=await get_bot_token())
        await bot.send_message(chat_id=user_telegram_id, text=text)
    except Exception:
        logger.exception("Failed to send payment notification to telegram_id=%s", user_telegram_id)


async def _notify_payment_channel(text: str) -> None:
    """Post a payment event to the payment channel (accounting feed).

    Skipped silently when payment_channel_id is not configured.
    Never raises — must not break webhook processing.
    """
    try:
        from app.bot.services.settings_service import (
            get_bot_token as _get_token,
            get_payment_channel_id,
        )

        channel_id = await get_payment_channel_id()
        if not channel_id:
            return
        bot = Bot(token=await _get_token())
        try:
            await bot.send_message(chat_id=channel_id, text=text)
        finally:
            await bot.session.close()
    except Exception:
        logger.exception("Failed to notify payment channel")


@router.post("/webhook/platega")
async def platega_webhook(request: Request) -> dict:
    """Handle Platega.io payment status webhooks.

    Verifies X-MerchantId + X-Secret headers, routes by status,
    updates Payment record, and notifies user via Bot.
    Always returns 200 OK to Platega (they retry on non-200).
    """
    # --- Header verification (T-05-04 mitigation) ---
    merchant_id = request.headers.get("X-MerchantId", "")
    secret = request.headers.get("X-Secret", "")

    expected_merchant, expected_secret = await get_platega_credentials()
    if merchant_id != expected_merchant or secret != expected_secret:
        logger.warning("Webhook rejected: invalid credentials (merchant_id=%s)", merchant_id)
        return {"error": "invalid credentials"}

    # --- Parse body ---
    body = await request.json()
    order_id: str = body.get("orderId", "")
    new_status_raw: str = body.get("status", "")
    transaction_id: str = body.get("transactionId", "")

    logger.info(
        "Webhook received: orderId=%s status=%s transactionId=%s",
        order_id,
        new_status_raw,
        transaction_id,
    )

    # --- Load payment by idempotency key ---
    payment = await get_payment(order_id)
    if payment is None:
        logger.warning("Webhook for unknown orderId=%s — returning OK (idempotent)", order_id)
        return {"status": "ok"}

    # --- Normalize status ---
    status_map = {
        "CONFIRMED": "succeeded",
        "CANCELED": "canceled",
        "CHARGEBACKED": "chargebacked",
        "REFUNDED": "refunded",
    }
    new_status = status_map.get(new_status_raw)
    if new_status is None:
        logger.warning("Webhook with unknown status=%s for orderId=%s", new_status_raw, order_id)
        return {"status": "ok"}

    # --- Validate transition (T-05-05 mitigation) ---
    if not _is_valid_transition(payment.status, new_status):
        logger.warning(
            "Invalid status transition: %s -> %s for orderId=%s",
            payment.status,
            new_status,
            order_id,
        )
        return {"status": "ok"}

    # --- Update payment atomically ---
    async with session_factory() as session:
        result = await session.execute(
            select(Payment).where(Payment.id == payment.id)
        )
        db_payment = result.scalar_one()
        db_payment.status = new_status
        if transaction_id:
            db_payment.platega_transaction_id = transaction_id
        if new_status == "succeeded":
            db_payment.paid_at = datetime.now(timezone.utc)
        await session.commit()

    # --- Load user for notification and channel access ---
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == payment.user_id)
        )
        user = result.scalar_one_or_none()

    if user is None:
        logger.error("User not found for payment orderId=%s user_id=%s", order_id, payment.user_id)
        return {"status": "ok"}

    # --- Route by status ---
    user_label = f"@{user.username}" if user.username else user.first_name
    amount_rub = payment.amount // 100
    bot = Bot(token=await get_bot_token())
    if new_status == "succeeded":
        await grant_access(user.id, bot)
        await _send_payment_notification(
            user.telegram_id,
            "Оплата прошла успешно! Доступ в канал открыт.",
        )
        await _notify_payment_channel(
            f"✅ Оплата {amount_rub}₽ — {user_label} (tg {user.telegram_id})\n"
            f"Заказ {order_id}"
        )
        # Calculate mentor commission
        commission = await calculate_commission(payment.id)
        if commission["amount"] > 0:
            await _send_payment_notification(
                commission["mentor_telegram_id"],
                f"Ваш реферал оплатил доступ! Начислено: {commission['amount']} руб.",
            )
            logger.info(
                "Commission calculated: %d kopecks for mentor %s from payment %s",
                commission["amount"],
                commission["mentor_id"],
                payment.id,
            )
    elif new_status == "canceled":
        await _send_payment_notification(
            user.telegram_id,
            "Оплата отменена. Вы можете попробовать снова.",
        )
        await _notify_payment_channel(
            f"❌ Оплата отменена — {user_label} (tg {user.telegram_id})\n"
            f"Заказ {order_id}"
        )
    elif new_status in ("chargebacked", "refunded"):
        await revoke_access(user.id, bot)
        await _send_payment_notification(
            user.telegram_id,
            "Возврат оформлен. Доступ в канал закрыт.",
        )
        await _notify_payment_channel(
            f"↩️ Возврат {amount_rub}₽ — {user_label} (tg {user.telegram_id})\n"
            f"Заказ {order_id}"
        )

    return {"status": "ok"}
