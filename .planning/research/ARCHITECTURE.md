# Architecture Patterns

**Domain:** Telegram quest platform with scheduled content delivery and payment integration
**Researched:** 2026-09-04
**Overall confidence:** HIGH

## System Architecture: 4-Process Modular Monolith

The platform runs as **4 distinct processes** sharing PostgreSQL + Redis, deployed via Docker Compose on a single VPS. This is the standard architecture for Telegram bot platforms with scheduled delivery and payments.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOCKER COMPOSE (single VPS)                         │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  BOT PROCESS  │  │ API PROCESS  │  │WORKER PROCESS│  │SCHEDULER PROC│   │
│  │   (aiogram)   │  │  (FastAPI)   │  │    (ARQ)     │  │ (APScheduler)│   │
│  │              │  │              │  │              │  │              │   │
│  │ User interact│  │ Payment hook │  │ Execute tasks│  │ Trigger jobs │   │
│  │ Commands     │  │ Admin API    │  │ Send messages│  │ at 08:00 etc │   │
│  │ Callbacks    │  │ Admin panel  │  │ Process pay  │  │ Cron triggers│   │
│  │ Inline keys  │  │ REST endpoints│  │ Retries      │  │              │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │            │
│         └─────────────────┼─────────────────┼─────────────────┘            │
│                           │                 │                              │
│                    ┌──────▼───────┐  ┌──────▼───────┐                     │
│                    │  PostgreSQL  │  │    Redis     │                     │
│                    │  (SQLAlchemy │  │  (ARQ queue  │                     │
│                    │   async 2.0) │  │   + cache)   │                     │
│                    └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why 4 processes, not fewer?

| Process | Reason | If merged |
|---------|--------|-----------|
| **Bot** (aiogram) | Long-polling/webhook for Telegram updates. Must be always-on, responsive to user input | Would block on payment webhooks or scheduled jobs |
| **API** (FastAPI) | Serves payment webhooks (needs fast 200 response), admin panel REST | Mixing webhook handling with bot polling creates race conditions |
| **Worker** (ARQ) | Executes queued tasks asynchronously. Separate process means jobs survive API restarts | If in-process, a crashed API loses all queued messages |
| **Scheduler** (APScheduler) | Triggers daily cron jobs. Must be singleton — running N times = N duplicate triggers | Must NOT run in Uvicorn worker (would fire per-worker) |

## Component Boundaries

### 1. Bot Process (aiogram 3.x)

**Responsibility:** All Telegram user interaction — commands, callbacks, inline keyboards, FSM states.

**Module structure** (feature-based, not layer-based):

```
bot/
├── main.py                    # Dispatcher setup, include routers
├── handlers/
│   ├── __init__.py
│   ├── registration.py        # /start, consent, archetype test
│   ├── scrolls.py             # Daily scroll delivery, completion marking
│   ├── reports.py             # Report submission (text, photo, video)
│   ├── profile.py             # XP, streak, stats viewing
│   ├── clans.py               # Clan management, invite, progress
│   ├── referrals.py           # Referral link generation, tracking
│   └── admin.py               # Admin-only commands (via middleware filter)
├── keyboards/
│   ├── __init__.py
│   ├── registration.py        # Registration flow keyboards
│   ├── scrolls.py             # Scroll action keyboards
│   └── common.py              # Shared back/menu buttons
├── states/
│   ├── __init__.py
│   └── registration.py        # FSM states for multi-step flows
├── filters/
│   ├── __init__.py
│   └── role.py                # IsAdmin, IsCurator, IsLeader filters
├── middlewares/
│   ├── __init__.py
│   ├── throttling.py          # Rate limiting per user
│   └── user_context.py        # Inject user data into handler context
└── config.py                  # Bot token, settings from env
```

**Key pattern:** Each feature gets its own `Router`. Routers are included in `Dispatcher` in dependency order — base handlers first, fallback handlers last.

```python
# bot/main.py
from aiogram import Dispatcher
from bot.handlers import registration, scrolls, reports, profile, clans, referrals

dp = Dispatcher()
dp.include_router(registration.router)    # First: handles /start
dp.include_router(scrolls.router)         # Then: scroll-specific
dp.include_router(reports.router)         # Then: report-specific
# ... fallback handlers included last
```

**Inter-process communication:** Bot process communicates with other processes ONLY through:
- **PostgreSQL** (shared state: user progress, scroll content, payment status)
- **Redis** (enqueue ARQ jobs when user action requires async work: send notification, process payment)

Bot does NOT directly call API, Worker, or Scheduler.

---

### 2. API Process (FastAPI)

**Responsibility:** Payment webhooks, admin panel REST API, health checks.

**Module structure:**

```
api/
├── main.py                    # FastAPI app, lifespan, CORS
├── routes/
│   ├── __init__.py
│   ├── webhooks.py            # POST /webhooks/yookassa — payment callbacks
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── scrolls.py         # CRUD for 90 scrolls (content management)
│   │   ├── users.py           # User management, role assignment
│   │   ├── finance.py         # Payments, commissions, prize fund
│   │   ├── moderation.py      # Reports review, ban/unban
│   │   └── audit.py           # Action audit log
│   └── health.py              # GET /health — liveness probe
├── schemas/
│   ├── __init__.py
│   ├── webhook.py             # YooKassa webhook event schema
│   └── admin/                 # Admin request/response schemas
├── dependencies.py            # DB session, auth, rate limiting
└── config.py                  # API keys, webhook secrets
```

**Critical pattern — webhook handler must be fast:**

```python
# api/routes/webhooks.py
from fastapi import APIRouter, Request, Response

router = APIRouter()

@router.post("/webhooks/yookassa")
async def yookassa_webhook(request: Request):
    event = await request.json()

    # 1. Validate IP (YooKassa whitelist)
    # 2. Enqueue async job — do NOT process inline
    await arq_pool.enqueue_job(
        "process_payment",
        payment_id=event["object"]["id"],
        event_type=event["event"],
        _job_id=f"payment:{event['object']['id']}:{event['event']}",
    )

    # 3. Respond 200 immediately — YooKassa retries for 24h on non-200
    return Response(status_code=200)
```

**Inter-process communication:**
- Receives webhooks from external payment providers
- Enqueues jobs to Redis (consumed by Worker)
- Reads/writes PostgreSQL directly
- Serves REST endpoints consumed by React admin panel

---

### 3. Worker Process (ARQ)

**Responsibility:** Execute all queued tasks — message delivery, payment processing, notifications, retries.

**Module structure:**

```
worker/
├── __init__.py
├── settings.py                # WorkerSettings: functions, cron_jobs, redis
├── tasks/
│   ├── __init__.py
│   ├── delivery.py            # send_daily_scroll, send_scroll_to_user
│   ├── payment.py             # process_payment, grant_access, revoke_access
│   ├── notifications.py       # send_reminder, send_streak_alert
│   ├── commissions.py         # calculate_commission, notify_mentor
│   └── referrals.py           # process_referral_binding
└── utils/
    ├── __init__.py
    └── rate_limiter.py         # Token bucket for Telegram API rate limits
```

**Key patterns:**

```python
# worker/settings.py
from arq.connections import RedisSettings
from worker.tasks import delivery, payment, notifications

class WorkerSettings:
    functions = [
        delivery.send_daily_scroll,
        delivery.send_scroll_to_user,
        payment.process_payment,
        payment.grant_access,
        notifications.send_reminder,
    ]
    cron_jobs = [
        # Daily scroll delivery trigger
        {
            "func": delivery.trigger_daily_delivery,
            "hour": 7,
            "minute": 55,  # Fire 5 min before 08:00 to queue messages
            "weekdays": [0, 1, 2, 3, 4, 5, 6],
        },
        # Streak reset at midnight (user's timezone)
        {
            "func": notifications.reset_streaks,
            "hour": 0,
            "minute": 5,
        },
    ]
    redis_settings = RedisSettings(host="redis", port=6379)
    max_tries = 3
    retry_delay = 60  # seconds between retries
```

**Idempotency is mandatory** — use `_job_id` for every job:

```python
# Duplicate enqueue with same _job_id is silently skipped
await arq_pool.enqueue_job(
    "send_scroll_to_user",
    user_id=123,
    scroll_id=45,
    _job_id=f"scroll:user:123:scroll:45",  # Stable dedup key
)
```

**Inter-process communication:**
- Reads jobs from Redis queue (enqueued by API, Scheduler, or Bot)
- Writes delivery status to PostgreSQL
- Sends messages via Telegram Bot API (via aiogram Bot instance)
- Does NOT receive HTTP requests — fully internal

---

### 4. Scheduler Process (APScheduler)

**Responsibility:** Trigger time-based jobs. This is the "clock" of the system.

**Module structure:**

```
scheduler/
├── __init__.py
├── main.py                    # APScheduler setup, job store config
├── jobs/
│   ├── __init__.py
│   ├── daily_scroll.py        # Triggers scroll delivery at 08:00
│   ├── streak_reset.py        # Resets streaks at midnight per timezone
│   ├── reminders.py           # Evening reminders for incomplete scrolls
│   └── analytics.py           # Daily stats aggregation
└── config.py                  # Timezone, schedule config
```

**Critical: APScheduler must run as singleton process.** If you run it inside Uvicorn with N workers, you get N duplicate triggers.

```python
# scheduler/main.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.triggers.cron import CronTrigger

jobstores = {
    "default": RedisJobStore(host="redis", port=6379, db=1)
}

scheduler = AsyncIOScheduler(jobstores=jobstores)

# Register jobs
scheduler.add_job(
    trigger_scroll_delivery,
    CronTrigger(hour=7, minute=55),
    id="daily_scroll_trigger",
    replace_existing=True,
)
```

**Inter-process communication:**
- Enqueues jobs to Redis (consumed by Worker)
- Does NOT interact with PostgreSQL directly
- Does NOT interact with Telegram Bot API

---

## Data Flow Patterns

### Flow 1: Daily Scroll Delivery (08:00)

```
Scheduler (07:55)
    │
    ├─ Enqueue "trigger_daily_delivery" job to Redis
    │
    ▼
Worker picks up job
    │
    ├─ Query PostgreSQL: SELECT users WHERE is_active=true AND paid=true
    │
    ├─ For each user (batch of 50):
    │   ├─ Enqueue "send_scroll_to_user" job with _job_id
    │   │
    │   ▼
    │   Worker picks up individual job
    │   │
    │   ├─ Rate limiter: wait if >25 msg/sec
    │   ├─ Query scroll content (respecting archetype)
    │   ├─ Send via Telegram Bot API
    │   ├─ Update PostgreSQL: delivery_status = 'sent'
    │   └─ If 429: re-enqueue with _defer_by = retry_after
    │
    └─ Log completion stats
```

### Flow 2: Payment → Access Grant

```
User clicks "Pay" in bot
    │
    ├─ Bot enqueues "create_payment" job
    │
    ▼
Worker creates payment via YooKassa API
    │
    ├─ Returns confirmation_url to user
    │
    ▼
User completes payment on YooKassa page
    │
    ├─ YooKassa sends webhook to API
    │
    ▼
API receives webhook
    │
    ├─ Respond 200 immediately
    ├─ Enqueue "process_payment" job with _job_id=payment:{id}:succeeded
    │
    ▼
Worker picks up job
    │
    ├─ Check idempotency: already processed? → skip
    ├─ BEGIN TRANSACTION:
    │   ├─ UPDATE payments SET status='succeeded'
    │   ├─ UPDATE users SET is_active=true, access_granted_at=NOW()
    │   ├─ INSERT INTO channel_invites (generate one-time link)
    │   ├─ INSERT INTO commissions (calculate mentor commission)
    │   └─ INSERT INTO audit_log
    │ └─ COMMIT
    ├─ Enqueue "send_access_grant" notification job
    └─ Done
```

### Flow 3: User Completes Scroll

```
User taps "Mark Complete" in bot
    │
    ├─ Bot updates PostgreSQL directly (fast path)
    │   ├─ UPDATE scrolls SET status='completed'
    │   ├─ UPDATE users SET xp = xp + 10, streak = streak + 1
    │   └─ INSERT INTO audit_log
    │
    ├─ Bot sends confirmation to user
    │
    └─ If report attached (text/photo/video):
        ├─ Enqueue "process_report" job
        │
        ▼
        Worker stores media (file_id + S3 backup)
        └─ Enqueue "notify_master" job
```

### Flow 4: Referral Binding

```
New user starts bot with ?ref=ABC123
    │
    ├─ Bot detects referral code in deep link
    ├─ Stores referrer_id in session state
    │
    ▼
User completes registration + payment
    │
    ├─ Enqueue "process_referral" job
    │
    ▼
Worker processes referral
    │
    ├─ BEGIN TRANSACTION:
    │   ├─ UPDATE users SET referrer_id = X
    │   ├─ INSERT INTO referrals
    │   ├─ UPDATE referrer SET referral_count = referral_count + 1
    │   └─ INSERT INTO commissions (referral bonus)
    │ └─ COMMIT
    └─ Enqueue "notify_referrer" job
```

## Database Schema Boundaries

PostgreSQL serves as the single source of truth. Key domain tables:

| Domain | Tables | Notes |
|--------|--------|-------|
| **Users** | `users`, `user_roles`, `referrals` | Telegram ID as unique key |
| **Content** | `scrolls`, `scroll_deliveries` | 90 scrolls, per-user delivery status |
| **Payments** | `payments`, `commissions`, `prize_fund` | Idempotent, audited |
| **Progress** | `user_progress`, `clans`, `clan_members` | XP, streak, clan aggregation |
| **Reports** | `reports`, `report_media` | Text/photo/video, master trail |
| **Admin** | `audit_log`, `system_settings` | Every action logged |
| **Tasks** | (Redis only) | ARQ job queue, not in PostgreSQL |

**Shared tables:** `users` is accessed by Bot (user interactions), API (admin queries), Worker (delivery lists). All access through SQLAlchemy 2.0 async sessions.

## Rate Limiting Architecture

Telegram enforces 3 independent throttles:

| Throttle | Limit | Impact if exceeded |
|----------|-------|--------------------|
| Per-chat | ~1 msg/sec | Individual user blocked |
| Per-group | 20 msg/min | Bot blocked in that group |
| Global bulk | ~30 msg/sec | **ALL users blocked** for `retry_after` seconds |

**Architecture solution:** Token bucket rate limiter in Worker process.

```
┌─────────────────────────────────────────────────────┐
│                  ARQ Worker                          │
│                                                     │
│  ┌──────────────┐    ┌──────────────────────────┐  │
│  │  Job Queue    │───▶│  Rate Limiter            │  │
│  │  (Redis)     │    │  (token bucket)          │  │
│  └──────────────┘    │  - 25 msg/sec global     │  │
│                      │  - 1 msg/sec per-chat    │  │
│                      └──────────┬───────────────┘  │
│                                 │                   │
│                      ┌──────────▼───────────────┐  │
│                      │  Telegram Bot API         │  │
│                      │  (aiogram Bot instance)   │  │
│                      └──────────────────────────┘  │
│                                                     │
│  On 429: re-enqueue job with _defer_by=retry_after │
└─────────────────────────────────────────────────────┘
```

For 500 users at 08:00: ~17 seconds total delivery time at 30 msg/sec. Manageable without paid broadcasts.

## Build Order (Component Dependencies)

Based on dependency analysis, the recommended build sequence:

```
Phase 1: Foundation (no external dependencies)
    ├── PostgreSQL schema + SQLAlchemy models
    ├── Redis connection pool
    ├── Bot skeleton (handlers, router system)
    └── API skeleton (FastAPI app, health check)

Phase 2: Core Loop (depends on Phase 1)
    ├── Registration flow (bot handlers)
    ├── Archetype test (bot + DB)
    ├── Scroll content CRUD (API admin)
    └── Basic scroll delivery (Worker + rate limiter)

Phase 3: Payments (depends on Phase 2)
    ├── YooKassa integration (API webhook + Worker)
    ├── Idempotent payment processing
    ├── Access grant → channel invite
    └── Commission calculation

Phase 4: Engagement (depends on Phase 2)
    ├── XP + streak system
    ├── Report submission + media handling
    ├── Referral system
    └── Clan system

Phase 5: Admin & Polish (depends on all above)
    ├── React admin panel
    ├── Audit log viewer
    ├── Prize fund distribution
    ├── Notifications/reminders
    └── Monitoring + alerting
```

**Why this order:**
- Phase 1 has zero external dependencies — pure infrastructure
- Phase 2 delivers the "daily scroll" core loop — the product's primary value
- Phase 3 unlocks monetization — can start collecting payments
- Phase 4 builds engagement on top of working delivery + payments
- Phase 5 is polish — admin can manage manually until panel is ready

## Anti-Patterns to Avoid

### Anti-Pattern 1: Processing webhooks inline
**What:** Doing business logic in the FastAPI webhook handler before responding 200
**Why bad:** YooKassa retries after 3s timeout → duplicate processing, or worse, lost webhooks
**Instead:** Respond 200 immediately, enqueue ARQ job for async processing

### Anti-Pattern 2: For-loop message sending
**What:** Iterating over user list with `await bot.send_message()` in a simple loop
**Why bad:** No crash recovery, no rate limiting, no progress tracking, blocks event loop
**Instead:** Use Redis-backed ARQ queue with rate limiter and idempotent job IDs

### Anti-Pattern 3: APScheduler inside Uvicorn workers
**What:** Running APScheduler in the FastAPI process with `uvicorn --workers N`
**Why bad:** N workers = N schedulers = N duplicate triggers for every cron job
**Instead:** Run APScheduler as a separate singleton process (Docker Compose service)

### Anti-Pattern 4: Sharing DB sessions between processes
**What:** Passing SQLAlchemy session from FastAPI to ARQ worker via `enqueue_job()`
**Why bad:** Sessions are not serializable, and processes have separate connection pools
**Instead:** Pass only IDs (user_id, payment_id), reconstruct DB access in worker

### Anti-Pattern 5: Streak reset by server timezone
**What:** Resetting all streaks at server midnight (UTC or Moscow time)
**Why bad:** Users in different timezones get unfair streak resets
**Instead:** Store each user's timezone, reset streaks per-user at their local midnight (use ARQ cron with timezone awareness)

## Scalability Considerations

| Concern | At 100 users | At 500 users | At 1K users |
|---------|--------------|--------------|-------------|
| Morning delivery | ~3 sec | ~17 sec | ~34 sec |
| DB connections | 5 pool | 10 pool | 20 pool |
| Redis memory | ~10 MB | ~50 MB | ~100 MB |
| VPS specs | 2 CPU, 2 GB | 2 CPU, 4 GB | 4 CPU, 8 GB |
| Process scaling | Single instance | Single instance | Consider separating Bot + Worker |

At 500 users (current target), a single VPS with Docker Compose is sufficient. No need for microservices or separate machines.

## Sources

- aiogram 3.x official docs (router system, middleware): HIGH confidence
- ARQ documentation + FastAPI-ARQ integration patterns: HIGH confidence
- Telegram Bot API rate limits (community-verified 2026 data): HIGH confidence
- YooKassa webhook documentation (idempotency, IP whitelist): HIGH confidence
- Modular monolith architecture patterns (DDD, import-linter): MEDIUM confidence
- Production bot templates (hirsiznerd/aiogram-moduled-structure, t1pson86/aiogram-bot-template): HIGH confidence
