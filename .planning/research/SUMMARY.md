# Project Research Summary

**Project:** Игрок.Реальность — Telegram quest platform
**Domain:** Telegram-based gamification platform (90-day challenge)
**Researched:** 2026-09-04
**Confidence:** MEDIUM-HIGH

## Executive Summary

Игрок.Реальность is a Telegram-first quest platform delivering daily personalized content (Свитки) to 500 users over a 90-day journey. The platform combines gamification (XP, streaks, leaderboards), social mechanics (clans, mentor commissions), and payments (YooKassa/CloudPayments) into a single-tenant bot experience. Experts build these platforms as **4-process modular monoliths** — separate bot, API, worker, and scheduler processes sharing PostgreSQL and Redis — deployed on a single VPS via Docker Compose.

The recommended stack uses **aiogram 3.x** for Telegram interaction, **FastAPI** for webhooks and admin API, **ARQ** for async task execution, and **PostgreSQL** with **SQLAlchemy 2.0** for persistent state. This combination handles Telegram's strict rate limits (30 msg/sec global, 1 msg/sec per chat) through a token-bucket rate limiter in the worker process, processes payment webhooks idempotently within 5 seconds, and scales comfortably to 500+ users on a 2 CPU / 4 GB VPS.

The top 3 risks are: (1) **Rate limit violations** at 08:00 morning delivery — preventable with rate limiting and batch scheduling, (2) **Payment idempotency failures** — preventable with database-level deduplication, and (3) **Timezone chaos** across Russia's 11 timezones — preventable by collecting user timezone at registration. All have documented mitigation patterns.

## Key Findings

### Recommended Stack

**Core technologies:**
- **Python 3.11+ / aiogram 3.31.0** — Telegram Bot API framework, native async, Pydantic v2 support
- **FastAPI 0.138.x** — REST API for webhooks and admin panel, auto OpenAPI docs
- **PostgreSQL 15+ / SQLAlchemy 2.0** — JSONB for flexible quest schemas, async via asyncpg
- **ARQ + Redis** — Lightweight async task queue (Celery overkill for 500 users)
- **APScheduler 3.11.3** — Cron triggers for daily content (must use 3.x, not 4.x alpha)
- **React 18 + Vite + Ant Design** — Admin panel SPA, ProTable/ProForm components
- **YooKassa SDK** — Payment processing with idempotency support

**Why not alternatives:** aiogram over python-telegram-bot (async-native), FastAPI over Django (lighter), ARQ over Celery (simpler, faster), PostgreSQL over MySQL (JSONB), Ant Design over Tailwind (admin components).

### Expected Features

**Must have (table stakes):**
- Daily Свиток delivery (08:00) — core value proposition
- Registration + archetype test (Head, Shell, Whirlwind, Ghost)
- Quest completion marking + XP/streak tracking
- Payment processing (YooKassa) + private channel access
- Referral system for viral growth
- Basic admin panel (CRUD for content/users)

**Should have (differentiators):**
- Personalized quest delivery by archetype
- Clan system with aggregated progress
- Curator/Leader mentor hierarchy
- Prize fund distribution
- Audit trail for all Master actions

**Defer to v2+:**
- Achievement badges — add if retention data supports it
- Archetype-specific quest variants — start universal, add variants in Phase 2
- Advanced analytics — Phase 3 if at all

### Architecture Approach

4-process modular monolith sharing PostgreSQL + Redis via Docker Compose on a single VPS. Each process has a distinct responsibility and communicates only through shared databases — no direct inter-process calls.

**Major components:**
1. **Bot Process (aiogram)** — User interaction: commands, callbacks, FSM states
2. **API Process (FastAPI)** — Payment webhooks, admin REST API, health checks
3. **Worker Process (ARQ)** — Execute queued tasks: delivery, payments, notifications
4. **Scheduler Process (APScheduler)** — Trigger time-based jobs (daily at 08:00, streak resets)

**Critical anti-patterns to avoid:**
- Processing webhooks inline (respond 200, enqueue async)
- APScheduler inside Uvicorn workers (N workers = N duplicate triggers)
- Sharing DB sessions between processes (pass IDs only)
- Server-timezone streak resets (use per-user timezone)

### Critical Pitfalls

1. **Rate limit time bomb at 08:00** — 500 simultaneous messages violate Telegram limits → bot ban. *Prevention: token-bucket rate limiter, stagger deliveries, 25 msg/sec max.*
2. **Payment webhook silent double-spend** — Webhook retries cause duplicate charge/grant. *Prevention: INSERT ON CONFLICT DO NOTHING, idempotency keys, DB transaction.*
3. **pre_checkout_query 10-second trap** — If validation takes >10s, transaction canceled. *Prevention: lightweight validation, pre-validate on invoice creation, cache results.*
4. **Streak burnout engine** — Hard resets at day 30+ cause most engaged users to quit. *Prevention: grace periods, 7-day capped cycles, recovery quests.*
5. **Timezone chaos** — 08:00 in Moscow = 03:00 in Vladivostok → bot blocks. *Prevention: collect timezone at registration, schedule per-segment.*

## Implications for Roadmap

### Phase 1: Foundation + Core Loop
**Rationale:** Infrastructure first (PostgreSQL, Redis, bot skeleton, API skeleton), then the daily scroll delivery mechanism — the product's primary value. Zero external dependencies in infrastructure.
**Delivers:** Bot skeleton with registration, archetype test, basic scroll delivery, XP/streak, basic leaderboard.
**Addresses:** Registration, archetype test, daily delivery, quest completion, XP/streak, leaderboard, private channel access.
**Avoids:** Long polling in production (use webhooks from day one).

### Phase 2: Payments + Access Control
**Rationale:** Unlocks monetization. Can start collecting payments immediately. Depends on Phase 2 core loop working.
**Delivers:** YooKassa integration, idempotent payment processing, access grant/revoke, referral system.
**Addresses:** Payment processing, referral system, private channel access, commission calculation.
**Avoids:** pre_checkout timeout, currency mismatch, webhook idempotency failures.

### Phase 3: Daily Delivery + Scheduling
**Rationale:** The 08:00 delivery blast is the hardest operational challenge. Must solve rate limiting before launch.
**Delivers:** APScheduler + ARQ worker with rate limiter, timezone-aware scheduling, evening reminders, unsubscribe mechanism.
**Addresses:** Daily delivery, notifications/reminders, timezone handling, unsubscribe.
**Avoids:** Rate limit violations, timezone chaos, missing unsubscribe.

### Phase 4: Engagement + Social
**Rationale:** Builds on working delivery + payments. Social mechanics drive retention.
**Delivers:** Clan system, curator/leader roles, mentor commission, prize fund, Master's Personal Path.
**Addresses:** Clan system, curator/leader roles, mentor commission, prize fund, personal path.
**Avoids:** Streak burnout (grace periods), empty leaderboards (clan-scoped).

### Phase 5: Admin Panel + Polish
**Rationale:** Admin can manage manually until panel is ready. Panel is polish, not blocking.
**Delivers:** React admin dashboard, audit trail, refund flow, monitoring/alerting.
**Addresses:** Web admin, audit trail, notifications queue.
**Avoids:** No audit trail, manual refund nightmare.

### Phase Ordering Rationale
- **Dependencies:** Phase 1 → 2 → 3 → 4 → 5 is the critical path (foundation → payments → delivery → engagement → polish)
- **Grouping:** Each phase delivers a complete, testable feature set
- **Pitfall avoidance:** Rate limits solved in Phase 3 before 08:00 blast; payment idempotency in Phase 2 before any money moves; timezone handling in Phase 3 before daily delivery
- **MVP validation:** Phase 1+2 deliver core value + monetization — enough to validate with real users

### Research Flags

**Needs research during planning:**
- **Phase 3 (Daily Delivery):** Rate limit tuning for 500 users, timezone segmentation strategy, APSPScheduler cron vs ARQ cron decision
- **Phase 2 (Payments):** YooKassa sandbox testing, webhook IP whitelist verification, pre_checkout_query validation strategy

**Standard patterns (skip research):**
- **Phase 1 (Foundation):** Well-documented aiogram/FastAPI setup, standard Docker Compose
- **Phase 4 (Engagement):** Clan/role patterns from existing Telegram bots
- **Phase 5 (Admin):** Ant Design Pro components, standard CRUD patterns

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against PyPI versions, official docs, 2026 benchmarks |
| Features | HIGH | Derived from TZ + competitive analysis of 8+ Telegram platforms |
| Architecture | HIGH | Standard 4-process pattern from production Telegram bots |
| Pitfalls | HIGH | Official Telegram docs + production experience reports |
| Payment integration | MEDIUM | YooKassa sandbox testing needed before confirming patterns |
| Rate limit tuning | MEDIUM | 30 msg/sec verified, but actual delivery time at 500 users needs testing |

**Overall confidence:** HIGH-MEDIUM

### Gaps to Address

- **YooKassa webhook IP whitelist:** Need to verify actual IP ranges in sandbox before production deployment
- **Timezone inference:** Telegram provides `language_code` but not timezone; may need to infer from locale or prompt user
- **Clan system edge cases:** Empty clans, clan dissolution, member migration — patterns exist but need validation
- **Archetype quest variants:** Content creation burden (4 variants × 90 days = 360 pieces) — defer to Phase 2+ unless content is ready
- **APScheduler vs ARQ cron:** Research suggests APScheduler as singleton, but ARQ has native cron — may simplify to single scheduler

---

*Research completed: 2026-09-04*
*Ready for roadmap: yes*
