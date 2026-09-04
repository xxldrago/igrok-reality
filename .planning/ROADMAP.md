# Roadmap: Игрок.Реальность

## Overview

A Telegram quest platform delivering 90-day challenges with gamification, payments via Platega.io, and admin oversight. The roadmap progresses from foundation through registration, quest delivery, progress tracking, payments, referrals, and finally admin management — each phase completing a vertical user story.

## Phases

- [ ] **Phase 1: Foundation** - Project scaffolding, database models, Docker infrastructure
- [ ] **Phase 2: Registration & Onboarding** - /start flow, consent, archetype test, user profiles
- [ ] **Phase 3: Quest Engine** - Content models, ARQ worker, 08:00 channel delivery
- [ ] **Phase 4: User Progress** - Completion tracking, XP, streaks, leaderboards
- [ ] **Phase 5: Payments & Access** - Platega.io integration, webhooks, channel access management
- [ ] **Phase 6: Referrals & Commission** - Referral links, tracking, commission calculation
- [ ] **Phase 7: Admin Panel** - React dashboard for users, scrolls, payments, settings

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
**Plans**: TBD

Plans:
- [ ] 01-01: Project structure, Docker Compose, environment config
- [ ] 01-02: SQLAlchemy models (User, Scroll, Payment, Referral, AuditLog)
- [ ] 01-03: Alembic migrations, base CRUD operations

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
**Plans**: TBD

Plans:
- [ ] 02-01: /start handler, consent flow, PDn compliance
- [ ] 02-02: Archetype test (4 questions) and assignment logic
- [ ] 02-03: User profile creation, referral link tracking

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
**Plans**: TBD

Plans:
- [ ] 03-01: Scroll CRUD, archetype-based content mapping
- [ ] 03-02: ARQ worker, APScheduler cron, 08:00 delivery spike handling
- [ ] 03-03: Delivery retry logic, pre-load 90 scrolls

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
**Plans**: TBD

Plans:
- [ ] 04-01: Button callback handler, XP award logic
- [ ] 04-02: Streak tracking with timezone-aware calculations
- [ ] 04-03: Leaderboard with real-time updates

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
**Plans**: TBD

Plans:
- [ ] 05-01: Platega.io API integration, payment initiation
- [ ] 05-02: Webhook handler, payment state machine
- [ ] 05-03: Channel access (invite links), revocation logic
- [ ] 05-04: Payment idempotency, mentor commission calculation

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
**Plans**: TBD

Plans:
- [ ] 06-01: Referral link generation, tracking on /start
- [ ] 06-02: Commission calculation, configurable rates
- [ ] 06-03: Commission balance tracking, manual payout

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
**Plans**: TBD

Plans:
- [ ] 07-01: React app setup, auth, routing
- [ ] 07-02: User management (list, search, details)
- [ ] 07-03: Scroll CRUD, payment management
- [ ] 07-04: Settings, audit log, role-based access

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/3 | Not started | - |
| 2. Registration & Onboarding | 0/3 | Not started | - |
| 3. Quest Engine | 0/3 | Not started | - |
| 4. User Progress | 0/3 | Not started | - |
| 5. Payments & Access | 0/4 | Not started | - |
| 6. Referrals & Commission | 0/3 | Not started | - |
| 7. Admin Panel | 0/4 | Not started | - |

## Parallel-Safe Opportunities

- **Phase 6 (Referrals) and Phase 5 (Payments)** can be partially parallelized: referral link generation (REF-01, REF-02) can begin while payment integration is in progress, but commission calculation (REF-03 through REF-07) depends on payment completion.
- **Phase 7 (Admin Panel)** frontend can be started in parallel with Phase 5 backend work — React app scaffolding and auth don't depend on payment logic.

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| REG-01 | Phase 2 | Pending |
| REG-02 | Phase 2 | Pending |
| REG-03 | Phase 2 | Pending |
| REG-04 | Phase 2 | Pending |
| REG-05 | Phase 2 | Pending |
| REG-06 | Phase 2 | Pending |
| REG-07 | Phase 2 | Pending |
| REG-08 | Phase 2 | Pending |
| QUEST-01 | Phase 3 | Pending |
| QUEST-02 | Phase 3 | Pending |
| QUEST-03 | Phase 3 | Pending |
| QUEST-04 | Phase 3 | Pending |
| QUEST-05 | Phase 3 | Pending |
| QUEST-06 | Phase 3 | Pending |
| COMP-01 | Phase 4 | Pending |
| COMP-02 | Phase 4 | Pending |
| COMP-03 | Phase 4 | Pending |
| COMP-04 | Phase 4 | Pending |
| COMP-05 | Phase 4 | Pending |
| COMP-06 | Phase 4 | Pending |
| COMP-07 | Phase 4 | Pending |
| PAY-01 | Phase 5 | Pending |
| PAY-02 | Phase 5 | Pending |
| PAY-03 | Phase 5 | Pending |
| PAY-04 | Phase 5 | Pending |
| PAY-05 | Phase 5 | Pending |
| PAY-06 | Phase 5 | Pending |
| PAY-07 | Phase 5 | Pending |
| PAY-08 | Phase 5 | Pending |
| PAY-09 | Phase 5 | Pending |
| PAY-10 | Phase 5 | Pending |
| PAY-11 | Phase 5 | Pending |
| REF-01 | Phase 6 | Pending |
| REF-02 | Phase 6 | Pending |
| REF-03 | Phase 6 | Pending |
| REF-04 | Phase 6 | Pending |
| REF-05 | Phase 6 | Pending |
| REF-06 | Phase 6 | Pending |
| REF-07 | Phase 6 | Pending |
| ADM-01 | Phase 7 | Pending |
| ADM-02 | Phase 7 | Pending |
| ADM-03 | Phase 7 | Pending |
| ADM-04 | Phase 7 | Pending |
| ADM-05 | Phase 7 | Pending |
| ADM-06 | Phase 7 | Pending |
| ADM-07 | Phase 7 | Pending |
| ADM-08 | Phase 7 | Pending |

**Total:** 47/47 requirements mapped ✓
