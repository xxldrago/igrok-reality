"""Payment service — Platega.io API client and payment CRUD."""

from __future__ import annotations

import uuid
from uuid import UUID

import httpx
from sqlalchemy import select

from app.shared.config import settings
from app.shared.database import session_factory
from app.shared.models.payment import Payment


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


async def call_platega_api(payment: Payment) -> dict:
    """Call Platega.io API to initiate a payment transaction.

    Updates payment.platega_transaction_id from the response.
    Returns the full response JSON.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.platega.io/v2/transaction/process",
            headers={
                "X-MerchantId": settings.PLATEGA_MERCHANT_ID,
                "X-Secret": settings.PLATEGA_SECRET,
            },
            json={
                "paymentMethod": 3,
                "paymentDetails": {"amount": payment.amount, "currency": payment.currency},
                "return": f"https://t.me/{settings.BOT_USERNAME}?start=payment_success",
                "failedUrl": f"https://t.me/{settings.BOT_USERNAME}?start=payment_failed",
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
