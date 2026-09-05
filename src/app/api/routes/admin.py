"""Admin API endpoints — commission payout and balance query."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.bot.services.commission import get_commission_balance, process_payout

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


class PayoutRequest(BaseModel):
    """Request body for manual commission payout."""

    user_id: UUID
    amount: int = Field(ge=1, description="Payout amount in kopecks")


@admin_router.post("/payout")
async def payout(request: PayoutRequest) -> dict:
    """Process a manual commission payout for a mentor.

    Deducts from pending balance, moves to paid_out, and creates an audit
    log entry.
    """
    result = await process_payout(request.user_id, request.amount)
    if not result["success"]:
        return {"status": "error", "error": result["error"], **result}
    return {"status": "ok", **result}


@admin_router.get("/commission/{user_id}")
async def commission_balance(user_id: UUID) -> dict:
    """Query commission balance for a user."""
    balance = await get_commission_balance(user_id)
    if balance is None:
        return {"status": "error", "error": "Commission balance not found"}
    return {"status": "ok", **balance}
