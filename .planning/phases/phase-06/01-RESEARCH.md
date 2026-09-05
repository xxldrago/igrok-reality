# Phase 6 Research: Referrals & Commission

## Overview

Phase 6 implements referral tracking, commission calculation, and balance management.

## Technical Approach

### Referral Link Generation

**Current state:** Referral links are already generated in registration flow (Plan 02-03). User model has `referral_code` field.

**Pattern:** Already implemented in `user_service.py`:
```python
def generate_referral_code() -> str:
    return uuid.uuid4().hex[:8]
```

### Referral Tracking on /start

**Current state:** `/start` handler in `registration.py` already parses deep_link and stores `referral_code` in FSM.

**Pattern:** Already implemented in `handle_start()`:
```python
if message.text and " " in message.text:
    referral_code = message.text.split(maxsplit=1)[1]
```

### Commission Calculation

**Current state:** `commission.py` has `calculate_commission()` that returns 10% for succeeded payments.

**One-time commission pattern:**
```python
async def calculate_commission(payment_id: UUID) -> dict:
    # Check if this is the user's first succeeded payment
    user_payments = await get_user_payments(user_id)
    succeeded_count = sum(1 for p in user_payments if p.status == "succeeded")
    
    if succeeded_count > 1:
        # Not first payment — no commission
        return {"amount": 0, "mentor_id": None, "mentor_telegram_id": None}
    
    # First payment — calculate commission
    commission = int(payment.amount * COMMISSION_RATE)
    return {"amount": commission, "mentor_id": str(mentor.id), ...}
```

### Commission Balance Tracking

**New model needed:** `CommissionBalance` table

```python
class CommissionBalance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Commission balance for mentors."""
    
    __tablename__ = "commission_balances"
    
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    total_earned: Mapped[int] = mapped_column(Integer, default=0)  # kopecks
    total_paid_out: Mapped[int] = mapped_column(Integer, default=0)  # kopecks
    pending: Mapped[int] = mapped_column(Integer, default=0)  # kopecks
    last_commission_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Configurable Commission Rate

**Pattern:**
```python
# In settings or database
COMMISSION_RATE = 0.10  # Default 10%

# Per-mentor override (optional)
class User(Base, ...):
    commission_rate: Mapped[float] = mapped_column(Float, default=0.10)
```

### Manual Payout

**Pattern:**
```python
async def process_payout(user_id: UUID, amount: int) -> dict:
    """Process manual payout for mentor commission."""
    balance = await get_commission_balance(user_id)
    if balance.pending < amount:
        return {"success": False, "error": "Insufficient balance"}
    
    # Deduct from pending, add to paid_out
    balance.pending -= amount
    balance.total_paid_out += amount
    await session.commit()
    
    # Send notification to mentor
    return {"success": True, "amount": amount}
```

## Integration Points

| Component | File | Integration |
|-----------|------|-------------|
| Models | `src/app/shared/models/commission.py` | NEW: CommissionBalance model |
| Services | `src/app/bot/services/commission.py` | Update: add balance tracking |
| Handlers | `src/app/bot/handlers/referral.py` | NEW: /referral command |
| API | `src/app/api/routes/admin.py` | NEW: admin payout endpoint |
| Migration | `alembic/versions/xxxx_add_commission_balances.py` | NEW |
