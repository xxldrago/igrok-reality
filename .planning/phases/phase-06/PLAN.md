---
phase: phase-06
type: execute
plans: 3
waves: 2
requirements: [REF-01, REF-02, REF-03, REF-04, REF-05, REF-06, REF-07]

# Wave structure
# Wave 1: 06-01 (CommissionBalance model + enhanced commission service)
# Wave 2: 06-02 (/referral handler + configurable rate) + 06-03 (admin payout) [parallel]

must_haves:
  truths:
    - "User receives a unique referral link after registration"
    - "Referral is tracked when new user joins via link (Referral record created)"
    - "One-time commission: only first succeeded payment per referee triggers commission"
    - "Commission percentage is configurable per mentor via settings"
    - "Commission balance is tracked per mentor in CommissionBalance table"
    - "Manual commission payout is possible via admin API"
  artifacts:
    - src/app/shared/models/commission.py
    - src/app/bot/handlers/referral.py
    - src/app/api/routes/admin.py
    - src/alembic/versions/20260905_add_commission_balances.py
  key_links:
    - "calculate_commission -> CommissionBalance -> session.commit"
    - "/referral handler -> user.referral_code -> link display"
    - "POST /api/admin/payout -> process_payout -> AuditLog"
    - "settings.COMMISSION_RATE -> calculate_commission"
---

# Phase 6: Referrals & Commission — Plan

**Goal: Users earn commissions by referring new participants**

## User Story

**As a** player who refers friends to the quest platform,
**I want** to share a unique referral link and earn commission when my referrals pay,
**so that** I am rewarded for bringing new participants.

## Plan Overview

| Plan | Name | Wave | Depends On | Requirements |
|------|------|------|------------|--------------|
| 06-01 | CommissionBalance model + enhanced commission service | 1 | — | REF-03, REF-06 |
| 06-02 | /referral handler + configurable rate | 2 | 06-01 | REF-01, REF-02, REF-04, REF-05 |
| 06-03 | Admin payout endpoint + balance query | 2 | 06-01 | REF-07 |

## Wave Execution

### Wave 1
- **06-01**: CommissionBalance model, Alembic migration, enhanced commission.py with one-time logic and balance persistence

### Wave 2 (parallel)
- **06-02**: /referral handler, configurable COMMISSION_RATE, Referral record creation on registration
- **06-03**: Admin payout endpoint, process_payout service, get_commission_balance, audit trail

## Success Criteria

1. User sends /referral and receives their unique referral link (https://t.me/BOT_USERNAME?start=CODE)
2. When new user joins via referral link, Referral record is created linking referrer to referee
3. On first succeeded payment by referee, mentor receives commission notification and balance is updated
4. Commission rate is configurable in settings (default 10%)
5. CommissionBalance tracks total_earned, total_pending, total_paid_out per mentor
6. Admin can call POST /api/admin/payout to process manual payout
7. Admin can call GET /api/admin/commission/{user_id} to view balance

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| One-time commission on first payment only | User decision — prevents abuse and simplifies tracking |
| CommissionBalance as separate table (not on User) | Clean separation of concerns, supports future multi-currency |
| Configurable rate in settings (not per-mentor field) | Simpler v1; per-mentor override can be added later via admin panel |
| process_payout creates AuditLog atomically | Audit trail for financial operations, no partial updates |

## Dependencies from Prior Phases

- **Phase 2**: User model has referral_code and referred_by_id fields
- **Phase 2**: /start handler parses deep link and stores referral_code in FSM
- **Phase 5**: commission.py has calculate_commission (pure calculation, no DB writes)
- **Phase 5**: Webhook CONFIRMED handler calls calculate_commission and notifies mentor
- **Phase 5**: Payment model with status, amount, user_id fields
- **Phase 1**: Alembic migration pattern established

## Coverage Audit

| Requirement | Plan | Covered |
|-------------|------|---------|
| REF-01 (Unique referral link) | 06-02 | /referral handler generates link |
| REF-02 (Referral tracking on /start) | 06-02 | create_user with referral_code creates Referral |
| REF-03 (Referrer reward) | 06-01 | calculate_commission + balance persistence |
| REF-04 (Referee reward) | 06-02 | Referee notification on referral join |
| REF-05 (Configurable commission %) | 06-02 | settings.COMMISSION_RATE |
| REF-06 (Commission tracking per mentor) | 06-01 | CommissionBalance model |
| REF-07 (Manual commission payout) | 06-03 | POST /api/admin/payout endpoint |

**All 7 requirements covered.** No gaps.
