# Roadmap: Игрок.Реальность

## Overview

A Telegram quest platform delivering 90-day challenges with gamification, payments via Platega.io, and admin oversight. The roadmap progresses from foundation through registration, quest delivery, progress tracking, payments, referrals, and finally admin management — each phase completing a vertical user story.

## Phases

- [x] **Phase 1: Foundation** - Project scaffolding, database models, Docker infrastructure
- [ ] **Phase 2: Registration & Onboarding** - /start flow, consent, archetype test, user profiles
- [ ] **Phase 3: Quest Engine** - Content models, ARQ worker, 08:00 channel delivery
- [ ] **Phase 4: User Progress** - Completion tracking, XP, streaks, leaderboards
- [ ] **Phase 5: Payments & Access** - Platega.io integration, webhooks, channel access management
- [ ] **Phase 6: Referrals & Commission** - Referral links, tracking, commission calculation
- [ ] **Phase 7: Admin Panel** - React dashboard for users, scrolls, payments, settings
- [ ] **Phase 8: Telegram Mini App Admin Panel** - Admin panel inside Telegram via /admin command
- [x] **Phase 9: TZ Gap Closure** - Close gaps between implementation and original technical specification

## Phase Details

### Phase 1: Foundation
**Goal**: Project is runnable with all infrastructure in place
**Depends on**: Nothing (first phase)
**Requirements**: None (infrastructure only)
**Success Criteria** (what must be TRUE):
  1. Developer can run `docker compose up` and all services start (bot, API, worker, scheduler)
  2. PostgreSQL database accepts migrations and all core tables exist
  3. Redis connection is established and functional
  4. Basic health check endpoint responds on FastAPI
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Docker infrastructure, pyproject.toml, shared kernel config
- [x] 01-02-PLAN.md — SQLAlchemy 2.0 async models (7 tables: users, referrals, scrolls, payments, user_completions, settings, audit_log)
- [x] 01-03-PLAN.md — Alembic migrations, FastAPI health check, all 4 process entrypoints

### Phase 2: Registration & Onboarding
**Goal**: Users can create accounts with archetype-based profiles
**Depends on**: Phase 1
**Requirements**: REG-01, REG-02, REG-03, REG-04, REG-05, REG-06, REG-07, REG-08
**Success Criteria** (what must be TRUE):
  1. User sends /start and sees welcome message with consent request
  2. User cannot proceed without providing consent
  3. User answers 4 archetype questions and receives Head/Shell/Whirlwind/Ghost classification
  4. User profile is created with Telegram data and archetype
  5. Referral link is tracked when user joins via referral
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — /start handler, consent flow, FSM foundation (Wave 1)
- [x] 02-02-PLAN.md — Archetype quiz (4 questions) and scoring logic (Wave 2)
- [x] 02-03-PLAN.md — User profile creation, referral link tracking (Wave 3)

### Phase 3: Quest Engine
**Goal**: Users receive personalized daily scrolls at 08:00 Moscow time
**Depends on**: Phase 2
**Requirements**: QUEST-01, QUEST-02, QUEST-03, QUEST-04, QUEST-05, QUEST-06
**Success Criteria** (what must be TRUE):
  1. Users receive a channel scroll at 08:00 Moscow time daily
  2. Scroll content is personalized based on user's archetype
  3. Scroll contains a completion button the user can tap
  4. Failed deliveries retry up to 3 times before logging error
  5. 90 scrolls are pre-loaded and ready for daily delivery
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Scroll service, User.started_at migration, 360 scrolls seed script (Wave 1)
- [x] 03-02-PLAN.md — ARQ delivery task, completion callback, keyboard, handler (Wave 2)
- [x] 03-03-PLAN.md — APScheduler cron wiring, unit tests, integration test (Wave 3)

### Phase 4: User Progress
**Goal**: Users see their completion streaks, XP, and leaderboard position
**Depends on**: Phase 3
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, COMP-07
**Success Criteria** (what must be TRUE):
  1. User taps completion button and receives XP confirmation
  2. Streak counter increments on completion and resets on miss
  3. Streak calculation respects user's local timezone
  4. Leaderboard shows ranked users by XP/streak
  5. Leaderboard updates in real-time after completions
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — Progress service layer, completion callback wiring, XP awards, leaderboard Redis write (Wave 1)
- [x] 04-02-PLAN.md — Streak tracking with timezone-aware calculations (Wave 2)
- [x] 04-03-PLAN.md — Leaderboard display, /progress and /leaderboard commands (Wave 2)

### Phase 5: Payments & Access
**Goal**: Users can purchase channel access via Platega.io
**Depends on**: Phase 4
**Requirements**: PAY-01, PAY-02, PAY-03, PAY-04, PAY-05, PAY-06, PAY-07, PAY-08, PAY-09, PAY-10, PAY-11
**Success Criteria** (what must be TRUE):
  1. User can initiate payment from bot and receives Platega.io payment link
  2. Webhook callback updates payment status correctly
  3. CONFIRMED status grants channel access via one-time invite link
  4. CANCELED status notifies user and allows retry
  5. CHARGEBACKED/REFUNDED status revokes channel access
  6. Payment is idempotent (no duplicate charges)
  7. Mentor commission is calculated per successful payment
**Plans:** 4 plans

Plans:
- [x] 05-01-PLAN.md — Platega.io API integration, payment initiation via inline keyboard (Wave 1)
- [x] 05-02-PLAN.md — Webhook handler, payment state machine, status notifications (Wave 2)
- [x] 05-03-PLAN.md — Channel access: one-time invite links, revocation logic (Wave 2)
- [x] 05-04-PLAN.md — Payment idempotency, mentor commission calculation (Wave 3)

### Phase 6: Referrals & Commission
**Goal**: Users earn commissions by referring new participants
**Depends on**: Phase 5
**Requirements**: REF-01, REF-02, REF-03, REF-04, REF-05, REF-06, REF-07
**Success Criteria** (what must be TRUE):
  1. User receives a unique referral link after registration
  2. Referral is tracked when new user joins via link
  3. Referrer and referee both receive configured rewards
  4. Commission percentage is configurable per mentor
  5. Commission balance is tracked per mentor
  6. Manual commission payout is possible via admin
**Plans:** 3 plans

Plans:
- [x] 06-01-PLAN.md — CommissionBalance model, Alembic migration, enhanced commission service with one-time logic (Wave 1)
- [x] 06-02-PLAN.md — /referral handler, configurable COMMISSION_RATE, Referral record creation (Wave 2)
- [x] 06-03-PLAN.md — Admin payout endpoint, process_payout service, balance query, audit trail (Wave 2)

### Phase 7: Admin Panel
**Goal**: Leaders and masters can manage all platform operations
**Depends on**: Phase 6
**Requirements**: ADM-01, ADM-02, ADM-03, ADM-04, ADM-05, ADM-06, ADM-07, ADM-08
**Success Criteria** (what must be TRUE):
  1. Admin can search and filter user list
  2. Admin can view detailed user profiles
  3. Admin can create, edit, and delete scrolls
  4. Admin can view payment list and details
  5. Admin can configure platform settings
  6. All admin actions are logged in audit trail
  7. Admin authentication restricts access to authorized roles
**Plans**: 4 plans

Plans:
- [x] 07-01-PLAN.md — React app scaffolding, JWT auth, routing (Wave 1)
- [x] 07-02-PLAN.md — User management: list, search, detail view (Wave 2)
- [x] 07-03-PLAN.md — Scroll CRUD, payment list and details (Wave 2)
- [x] 07-04-PLAN.md — Settings, audit log, role-based access (Wave 3)

### Phase 8: Telegram Mini App Admin Panel
**Goal**: Admin can manage the platform from inside Telegram via Mini App
**Depends on**: Phase 7
**Requirements**: ADM-01, ADM-02, ADM-03, ADM-04, ADM-05, ADM-06, ADM-07, ADM-08
**Success Criteria** (what must be TRUE):
  1. Admin can open admin panel inside Telegram via /admin command
  2. Telegram initData authentication works (HMAC validation)
  3. Admin panel renders correctly in Telegram WebView (mobile-optimized)
  4. Web admin panel at /admin/ still works unchanged
  5. All admin operations (users, scrolls, payments, settings, audit) work in TMA
  6. Role-based access control works in TMA (master, leader, curator)
**Plans**: 3 plans

Plans:
- [x] 08-01-PLAN.md — Backend: role column, Telegram auth, TMA API, static serving (Wave 1)
- [x] 08-02-PLAN.md — Frontend: TMA React app with Telegram auth, mobile layout (Wave 2)
- [x] 08-03-PLAN.md — Bot: /admin command with WebAppInfo button, deep links (Wave 2)

### Phase 9: TZ Gap Closure
**Goal**: Close the gaps between the implemented platform and the original technical specification (ТЗ v1.0, 21.08.2026), excluding payment-provider integration differences. Restructure content model, add player-facing commands and reports, roles/groups/clans, economy tuning, master-chat integration, and admin extensions.
**Depends on**: Phase 8
**Requirements**: GAP-01, GAP-02, GAP-03, GAP-04, GAP-05, GAP-06, GAP-07, GAP-08, GAP-09, GAP-10, GAP-11, GAP-12, GAP-13, GAP-14
**Success Criteria** (what must be TRUE):
  1. Scroll content is structured into 5 sections (common task, individual archetype task, morning ritual, habits, micromovements), stored per-archetype, editable via admin
  2. Daily scroll is published to the closed channel AND delivered privately at the configurable 08:00 time
  3. Player can attach a report (text/photo/video) when completing a scroll; report duplicates to Master's private chat
  4. `/profile` shows archetype, quest day, XP, streak, role, payment status, and referral link
  5. `/myteam` lets a curator view their group (up to 10 players) with streak and payment status
  6. Groups, Specialist role, role transitions with history, and Clans are implemented per access matrix
  7. XP weights are configurable and streak bonuses exist at days 7/30/90
  8. Prize fund reserves a configurable % of stream income and supports distribution rules
  9. Admin panel gains dashboard, finance, moderation, and structured settings modules; role transitions via admin
  10. Reminders/notifications fire (scroll not done, streak-loss warning)
**Plans**: 6 plans

Plans:
- [x] 09-01-PLAN.md — Content model restructure: 5-section scroll, archetypes table, scroll_archetype_tasks, migration, seed (Wave 1)
- [x] 09-02-PLAN.md — Player bot: /profile, /myteam, report attachment, channel publishing flow (Wave 1)
- [x] 09-03-PLAN.md — Roles & groups: groups model, Specialist role, role transitions + history, Clans (Wave 2)
- [x] 09-04-PLAN.md — Economy: configurable XP weights, streak bonuses 7/30/90, Prize Fund (Wave 2)
- [x] 09-05-PLAN.md — Lichnaya Trope & notifications: master-chat duplication, reminders, system notifications (Wave 3)
- [x] 09-06-PLAN.md — Admin extensions: dashboard, finance, moderation, structured settings, supplementary-quest editor (Wave 3)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-09-04 |
| 2. Registration & Onboarding | 3/3 | Complete | 2026-09-04 |
| 3. Quest Engine | 3/3 | Complete | 2026-09-05 |
| 4. User Progress | 3/3 | Complete | 2026-09-05 |
| 5. Payments & Access | 4/4 | Complete | 2026-09-05 |
| 6. Referrals & Commission | 3/3 | Complete | 2026-09-05 |
| 7. Admin Panel | 4/4 | Complete | 2026-09-06 |
| 8. Telegram Mini App | 3/3 | Complete | 2026-09-06 |
| 9. TZ Gap Closure | 6/6 | Complete | 2026-09-09 |

## Parallel-Safe Opportunities

- **Phase 6 (Referrals) and Phase 5 (Payments)** can be partially parallelized: referral link generation (REF-01, REF-02) can begin while payment integration is in progress, but commission calculation (REF-03 through REF-07) depends on payment completion.
- **Phase 7 (Admin Panel)** frontend can be started in parallel with Phase 5 backend work — React app scaffolding and auth don't depend on payment logic.
- **Phase 8 (TMA)** Plans 08-02 (frontend) and 08-03 (bot) can run in parallel in Wave 2 after Plan 08-01 (backend) completes.

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| REG-01 | Phase 2 | Complete |
| REG-02 | Phase 2 | Complete |
| REG-03 | Phase 2 | Complete |
| REG-04 | Phase 2 | Complete |
| REG-05 | Phase 2 | Complete |
| REG-06 | Phase 2 | Complete |
| REG-07 | Phase 2 | Complete |
| REG-08 | Phase 2 | Complete |
| QUEST-01 | Phase 3 | Complete |
| QUEST-02 | Phase 3 | Complete |
| QUEST-03 | Phase 3 | Complete |
| QUEST-04 | Phase 3 | Complete |
| QUEST-05 | Phase 3 | Complete |
| QUEST-06 | Phase 3 | Complete |
| COMP-01 | Phase 4 | Complete |
| COMP-02 | Phase 4 | Complete |
| COMP-03 | Phase 4 | Complete |
| COMP-04 | Phase 4 | Complete |
| COMP-05 | Phase 4 | Complete |
| COMP-06 | Phase 4 | Complete |
| COMP-07 | Phase 4 | Complete |
| PAY-01 | Phase 5 | Complete |
| PAY-02 | Phase 5 | Complete |
| PAY-03 | Phase 5 | Complete |
| PAY-04 | Phase 5 | Complete |
| PAY-05 | Phase 5 | Complete |
| PAY-06 | Phase 5 | Complete |
| PAY-07 | Phase 5 | Complete |
| PAY-08 | Phase 5 | Complete |
| PAY-09 | Phase 5 | Complete |
| PAY-10 | Phase 5 | Complete |
| PAY-11 | Phase 5 | Complete |
| REF-01 | Phase 6 | Complete |
| REF-02 | Phase 6 | Complete |
| REF-03 | Phase 6 | Complete |
| REF-04 | Phase 6 | Complete |
| REF-05 | Phase 6 | Complete |
| REF-06 | Phase 6 | Complete |
| REF-07 | Phase 6 | Complete |
| ADM-01 | Phase 7 | Complete |
| ADM-02 | Phase 7 | Complete |
| ADM-03 | Phase 7 | Complete |
| ADM-04 | Phase 7 | Complete |
| ADM-05 | Phase 7 | Complete |
| ADM-06 | Phase 7 | Complete |
| ADM-07 | Phase 7 | Complete |
| ADM-08 | Phase 7 | Complete |
| ADM-01 | Phase 8 | Complete |
| ADM-02 | Phase 8 | Complete |
| ADM-03 | Phase 8 | Complete |
| ADM-04 | Phase 8 | Complete |
| ADM-05 | Phase 8 | Complete |
| ADM-06 | Phase 8 | Complete |
| ADM-07 | Phase 8 | Complete |
| ADM-08 | Phase 8 | Complete |
| GAP-01 | Phase 9 | Complete |
| GAP-02 | Phase 9 | Complete |
| GAP-03 | Phase 9 | Complete |
| GAP-04 | Phase 9 | Complete |
| GAP-05 | Phase 9 | Complete |
| GAP-06 | Phase 9 | Complete |
| GAP-07 | Phase 9 | Complete |
| GAP-08 | Phase 9 | Complete |
| GAP-09 | Phase 9 | Complete |
| GAP-10 | Phase 9 | Complete |
| GAP-11 | Phase 9 | Complete |
| GAP-12 | Phase 9 | Complete |
| GAP-13 | Phase 9 | Complete |
| GAP-14 | Phase 9 | Complete |

**Total:** 70/70 requirements mapped ✓
