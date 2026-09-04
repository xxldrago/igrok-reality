# Technology Stack

**Project:** Игрок.Реальность — Telegram quest platform
**Researched:** 2026-09-04
**Confidence:** MEDIUM (verified websearch results, PyPI version data, official docs)

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11+ | Runtime | aiogram 3.x requires 3.10+, best performance at 3.11+ with task groups |
| aiogram | 3.31.0 | Telegram Bot API framework | Latest stable (Aug 2026), full Bot API 10.3 support, native Pydantic v2, Scenes FSM, middleware system. Active development with monthly releases. |
| FastAPI | 0.138.x | REST API for admin panel + webhooks | Latest stable, native Pydantic v2, async-first, auto OpenAPI docs for admin panel. Perfect fit for webhook receivers. |
| Pydantic | 2.13.5 | Data validation, settings, schemas | Rust core = 17x faster than v1. Required by both aiogram 3.x and FastAPI. Use `pydantic-settings` for env config. |

**Why not python-telegram-bot:** Synchronous-first design, heavier, less idiomatic for asyncio stacks. aiogram is the de facto standard for async Telegram bots in the Russian-speaking community with better ecosystem for this use case.

**Why not Django/DRF:** Overkill for a Telegram-first platform. FastAPI's async model matches Telegram webhook handling better.

### Database

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL | 15+ | Primary database | JSONB for flexible quest/scoring schemas, mature async support via asyncpg, row-level security for multi-role access. |
| SQLAlchemy | 2.0.x | ORM + async DB access | `async_sessionmaker` + `create_async_engine` with `asyncpg` driver. `expire_on_commit=False` critical for async contexts. Connection pool: `pool_size=5, max_overflow=10, pool_pre_ping=True`. |
| Alembic | 1.13+ | Database migrations | Native SQLAlchemy 2.0 integration, async migration support. |

**Why not raw SQL:** Type safety, migration management, relationship handling for clans/roles/commissions.

**Why not Tortoise ORM:** Less mature, smaller community, fewer production battle-tested patterns for complex financial data.

### Task Queue & Scheduling

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| ARQ | 0.28+ | Background task queue | Async-native Redis queue, lighter than Celery, perfect for 500-user scale. Supports `defer_until` for scheduled delivery, retry with backoff, cron jobs. |
| Redis | 7.x | ARQ broker + caching + rate limiting | Shared between ARQ (task queue), aiogram (FSM storage), rate limiting (Telegram 30msg/sec global, 1msg/sec per chat), and session caching. |
| APScheduler | 3.11.3 | Cron triggers for daily content | Stable, `AsyncIOScheduler` + `BackgroundScheduler` for reliable 08:00 publish triggers. **Use 3.x, NOT 4.x** (still alpha, API unstable since Apr 2025). |

**Why not Celery:** Overhead of broker setup, heavier memory footprint, sync-first design. ARQ handles 12,500 tasks/sec vs Celery's 2,800 in benchmarks — more than sufficient for 500 users.

**Why APScheduler 3.x over 4.x:** 4.x has been alpha since Aug 2022 with no stable release. The `AsyncIOScheduler` in 3.x handles async jobs natively. Use `SQLAlchemyJobStore` (sync) for job persistence — the job store being sync is acceptable at this scale.

**Critical pattern:** APScheduler triggers the "time to publish" event, ARQ executes the actual delivery (message sending with rate limiting). This separation ensures reliable scheduling independent of worker availability.

### Admin Panel

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 18.x | UI framework | Mature, TypeScript-first, vast ecosystem for admin components. |
| Vite | 5.x | Build tool | 40x faster dev server than CRA, native ESM, optimized Rollup production builds. |
| TypeScript | 5.x | Type safety | Catches admin panel bugs early, API contract alignment with FastAPI auto-generated OpenAPI. |
| Ant Design | 5.x | Component library | Full admin panel component set (tables, forms, charts), strong Russian localization, battle-tested at scale. |
| Zustand | 5.x | State management | Lightweight (1KB), simpler than Redux for admin panel state. |
| React Router | 6.x | Routing | Standard choice, nested routes for admin sections. |

**Why not Next.js:** SPA is sufficient for admin panel. SSR adds complexity without benefit for an internal tool.

**Why not Tailwind:** Ant Design's pre-built admin components (ProTable, ProForm) accelerate development significantly for CRUD-heavy admin interfaces.

### Payments

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| yookassa | latest | Payment processing | Official Python SDK from YooMoney. Supports `Idempotence-Key` header for idempotent operations. Webhook verification via API re-fetch. |
| CloudPayments | API v1 | Alternative payment processor | Fallback option. Similar webhook pattern. |

**Idempotency pattern (CRITICAL):** Store `event_id` from webhook in PostgreSQL with `INSERT ... ON CONFLICT DO NOTHING`. Process payment only if insert succeeds. This prevents double-charging from webhook retries. Keep idempotency keys for 48 hours (TTL cleanup).

**Webhook flow:**
1. Receive webhook → return 200 immediately (within 5 seconds)
2. Enqueue ARQ job with full payload
3. ARQ worker: verify signature → check idempotency key → update payment status → grant access → calculate commission

### Media Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| S3-compatible storage | — | Media backup | Store file_ids + backup copies for user submissions. Protects against Telegram CDN deletion. |
| aiofiles | latest | Async file I/O | For local temp files during media processing. |

### Development & Infrastructure

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Docker Compose | v2 | Local dev + deployment | Single `docker-compose.yml` for bot, API, worker, PostgreSQL, Redis. Russian VPS compatible (152-FZ). |
| uvicorn | latest | ASGI server | FastAPI + aiogram ASGI server. |
| pytest | 8.x | Testing | `pytest-asyncio` for async test support. |
| Ruff | latest | Linter + formatter | Replaces flake8 + black + isort. Single tool, Rust-fast. |
| Alembic | 1.13+ | DB migrations | Async migration support for SQLAlchemy 2.0. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `aiolimiter` | latest | Rate limiting | Telegram message queue — 1msg/sec per chat, 30msg/sec global |
| `aiohttp` | 3.x | HTTP client | Outgoing webhooks, external API calls |
| `python-dotenv` | latest | Env loading | Local development environment |
| `sentry-sdk` | latest | Error tracking | Production error monitoring |
| `structlog` | latest | Structured logging | Production logging with context |
| `python-multipart` | latest | File uploads | Admin panel file uploads, user media submissions |
| `httpx` | latest | Async HTTP client | Modern alternative to aiohttp for simpler cases |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Telegram framework | aiogram 3.31 | python-telegram-bot | Sync-first, heavier, less idiomatic for asyncio |
| API framework | FastAPI | Django REST | Too heavy for Telegram-first platform |
| ORM | SQLAlchemy 2.0 | Tortoise ORM | Less mature for complex financial data |
| Task queue | ARQ | Celery | Overkill, heavier, sync-first |
| Scheduler | APScheduler 3.11 | Celery Beat | Part of Celery ecosystem (avoided) |
| Admin UI | Ant Design | Material UI / Chakra | Ant Design has better admin-specific components |
| State mgmt | Zustand | Redux Toolkit | Overkill for admin panel |
| DB | PostgreSQL | MySQL | JSONB support critical for flexible schemas |
| Cache/Queue | Redis | RabbitMQ | Redis handles both queue and cache roles |

## Installation

```bash
# Backend core
pip install "aiogram>=3.31" "fastapi>=0.138" "uvicorn[standard]" "pydantic>=2.13" "pydantic-settings>=2.0"

# Database
pip install "sqlalchemy[asyncio]>=2.0" "asyncpg>=0.30" "alembic>=1.13"

# Task queue & scheduling
pip install "arq>=0.28" "redis>=5.0" "apscheduler>=3.11"

# Payments
pip install "yookassa>=3.0"

# Media & HTTP
pip install "aiofiles" "httpx" "python-multipart"

# Dev tools
pip install "pytest" "pytest-asyncio" "ruff" "structlog" "sentry-sdk[fastapi]"

# Frontend (admin panel)
npm create vite@latest admin -- --template react-ts
cd admin
npm install antd @ant-design/pro-components zustand react-router-dom axios
```

## Sources

- aiogram 3.31.0 docs (docs.aiogram.dev, released Aug 26 2026)
- FastAPI 0.138.x release notes (fastapi.tiangolo.com)
- Pydantic v2.13.5 GitHub releases (github.com/pydantic/pydantic)
- ARQ documentation (arq-docs.helpmanual.io) + FastAPI-ARQ integration patterns
- APScheduler 3.11.3 PyPI (released Jun 28 2026) — confirmed 4.x still alpha
- SQLAlchemy 2.0 async docs (docs.sqlalchemy.org)
- YooKassa Python SDK (github.com/yoomoney/yookassa-sdk-python)
- Telegram Bot API rate limits: 30msg/sec global, 1msg/sec per chat, 20msg/min per group (verified Aug 2026)
- React 18 + Vite + Ant Design admin templates (github.com/larry-xue/react-admin-dashboard)
- Payment webhook idempotency patterns (martinuke0.github.io, dev.to)
