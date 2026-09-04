# AGENTS.md — Instructions for AI Coding Agents

## Project Overview

**Игрок.Реальность** — Telegram-based 90-day gamified quest platform.

- **Users:** ~500 players, 5 curators, 1 leader, 1 master
- **Stack:** Python 3.11+, aiogram 3.31, FastAPI, PostgreSQL 15+, Redis, ARQ, React + Vite
- **Payment Provider:** Platega.io
- **Architecture:** Modular monolith (4 processes: bot, API, worker, scheduler)

## Development Workflow

This project uses GSD (Get Stuff Done) workflow.

### Key Commands

- `/gsd-next` — Detect project state and route to next action
- `/gsd-plan-phase N` — Create detailed plan for phase N
- `/gsd-execute-phase N` — Execute phase N with wave parallelization
- `/gsd-verify-work` — Run UAT verification
- `/gsd-code-review` — Review code for bugs/security/quality
- `/gsd-ship` — Create PR and prepare for merge

### Project Structure

```
.planning/
├── PROJECT.md          # Project context (stack, architecture, decisions)
├── REQUIREMENTS.md     # 47 v1 requirements with traceability
├── ROADMAP.md          # 7 phases with goals and deliverables
├── STATE.md            # Current workflow state
├── config.json         # GSD workflow configuration
├── research/           # Research findings (STACK, FEATURES, ARCHITECTURE, PITFALLS)
└── phases/             # Phase plans and execution artifacts
```

## Architecture

### Processes

1. **Bot** — Telegram bot (aiogram 3.31)
2. **API** — REST API (FastAPI)
3. **Worker** — Background tasks (ARQ)
4. **Scheduler** — Cron jobs (APScheduler)

### Key Technical Decisions

1. **aiogram 3.31** — Async Telegram framework
2. **FastAPI** — REST API for webhooks + admin panel
3. **PostgreSQL 15+** — Primary database
4. **Redis** — Cache + message broker for ARQ
5. **ARQ** — Async task queue for message delivery
6. **APScheduler** — Cron triggers for daily scroll delivery
7. **Platega.io** — Payment processing (СБП, cards, crypto)
8. **React + Vite** — Admin panel frontend

### Database Schema

Core tables:
- `users` — Telegram user data, archetype, XP, streak
- `referrals` — Referral relationships
- `payments` — Payment transactions
- `scrolls` — Daily quest content (90 days)
- `user_completions` — Quest completion records
- `clans` — Clan data (v2)
- `settings` — Platform configuration
- `audit_log` — Admin action history

## Code Conventions

### Python
- Follow PEP 8
- Use async/await for all I/O operations
- Type hints required for all function signatures
- Docstrings for public functions

### Database
- Use SQLAlchemy 2.0 async style
- Alembic for migrations
- All tables have `created_at` and `updated_at` timestamps
- Use UUIDs for primary keys

### Telegram Bot
- Use aiogram 3.x dispatcher pattern
- Router-based handler organization
- FSM for multi-step flows (registration, payment)
- InlineKeyboard for user interactions

### API
- RESTful endpoints
- Pydantic models for request/response
- OpenAPI documentation auto-generated
- Health check at `/health`

## Environment Variables

```bash
# Telegram
BOT_TOKEN=
MASTER_CHANNEL_ID=
QUEST_CHANNEL_ID=
PAYMENT_CHANNEL_ID=

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/igrok

# Redis
REDIS_URL=redis://localhost:6379/0

# Platega.io
PLATEGA_MERCHANT_ID=
PLATEGA_SECRET=
PLATEGA_WEBHOOK_URL=

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
TZ=Europe/Moscow
```

## Testing

### Unit Tests
```bash
pytest tests/unit/ -v
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### E2E Tests
```bash
pytest tests/e2e/ -v
```

## Deployment

### Docker
```bash
docker compose up -d
```

### Services
- `bot` — Telegram bot process
- `api` — FastAPI server
- `worker` — ARQ background worker
- `scheduler` — APScheduler cron jobs
- `postgres` — PostgreSQL database
- `redis` — Redis cache/broker

## Common Pitfalls

1. **Timezone handling** — Always use `datetime.now(timezone.utc)` for comparisons. Store user timezone separately.
2. **Rate limits** — Telegram Bot API: 20-25 msg/sec. Queue all outgoing messages.
3. **Payment webhooks** — Verify `X-MerchantId` and `X-Secret` headers. Implement idempotency.
4. **Streak calculation** — Use user's timezone, not server timezone. Reset at midnight user time.
5. **Channel access** — One-time invite links expire. Regenerate if user hasn't joined.

## GSD Configuration

```json
{
  "auto_mode": "YOLO",
  "default_granularity": "standard",
  "parallel_execution": true,
  "git_tracking": true,
  "drift_guard": true,
  "plan_check": "ON"
}
```

---

*Last updated: 2026-09-04*
