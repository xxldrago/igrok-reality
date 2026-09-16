# DB_SCHEMA.md — Database Schema Reference

Generated from `src/app/shared/models/`. All tables use UUID primary keys (`UUIDPrimaryKeyMixin`) and most use `TimestampMixin` (created_at, updated_at). PostgreSQL dialect.

---

## 1. `users`
**Model:** `User` — Telegram user data, archetype, XP, streak.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL, server_default now() |
| updated_at | DateTime(tz) | NOT NULL, server_default now(), onupdate now() |
| telegram_id | BigInteger | UNIQUE, INDEX, NOT NULL |
| first_name | String(255) | default "" |
| last_name | String(255) | nullable |
| username | String(255) | nullable |
| archetype | String(50) | nullable (head/shell/whirlwind/ghost) |
| xp | Integer | default 0 |
| streak | Integer | default 0 |
| streak_last_date | Date | nullable |
| is_active | Boolean | default False |
| paid_at | DateTime(tz) | nullable |
| access_granted_at | DateTime(tz) | nullable |
| referral_code | String(20) | UNIQUE, nullable |
| referred_by_id | UUID | FK → users.id, nullable (self-referral) |
| timezone | String(50) | default "Asia/Krasnoyarsk" |
| role | String(50) | default "player" |
| started_at | DateTime(tz) | nullable |
| group_id | UUID | FK → groups.id, nullable |
| clan_id | UUID | FK → clans.id, nullable |

**Relationships:**
- User → User (self): referred_by_id (many-to-one)
- User → Group: group_id (many-to-one)
- User → Clan: clan_id (many-to-one)

---

## 2. `referrals`
**Model:** `Referral` — Referral relationships between users.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL, server_default now() |
| updated_at | DateTime(tz) | NOT NULL, server_default now(), onupdate now() |
| referrer_id | UUID | FK → users.id, NOT NULL |
| referee_id | UUID | FK → users.id, UNIQUE, NOT NULL |

**Constraints:** UNIQUE(referrer_id, referee_id)

**Relationships:**
- Referral → User: referrer_id (many-to-one)
- Referral → User: referee_id (many-to-one, one-to-one)

---

## 3. `scrolls`
**Model:** `Scroll` — Daily quest content (90 days, 5-section structure).

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| day_number | Integer | NOT NULL, UNIQUE (1–90) |
| common_task | Text | NOT NULL |
| ritual | Text | NOT NULL |
| habits | Text | NOT NULL |
| micromovements | Text | NOT NULL |
| media_file_id | String(255) | nullable |
| published_at | DateTime(tz) | nullable |

**Relationships:**
- One-to-many: Scroll → ScrollArchetypeTask
- Referenced by: UserCompletion.scroll_id

---

## 4. `scroll_types`
**Model:** `ScrollType` — Defines the 9 scroll types with commands and schedules.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| code | String(30) | UNIQUE, NOT NULL |
| name | String(100) | NOT NULL |
| command | String(30) | NOT NULL |
| hour | Integer | NOT NULL |
| minute | Integer | NOT NULL, default 0 |
| xp_reward | Integer | NOT NULL, default 0 |
| description | Text | NOT NULL, default "" |
| requires_meditation | Boolean | NOT NULL, default False |
| is_breathing_day_only | Boolean | NOT NULL, default False |
| is_awareness_day_only | Boolean | NOT NULL, default False |
| sort_order | Integer | NOT NULL, default 0 |

**Relationships:**
- Referenced by: DailyScroll.scroll_type_id
- Referenced by: UserDailyCommand.scroll_type_id

---

## 5. `scroll_archetype_tasks`
**Model:** `ScrollArchetypeTask` — Per-archetype individual task for each scroll.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| scroll_id | UUID | FK → scrolls.id, INDEX, NOT NULL |
| archetype_code | String(50) | NOT NULL |
| task_text | Text | NOT NULL |

**Constraints:** UNIQUE(scroll_id, archetype_code)

**Relationships:**
- ScrollArchetypeTask → Scroll: scroll_id (many-to-one)

---

## 6. `archetypes`
**Model:** `Archetype` — Reference table of the 4 player archetypes.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| code | String(50) | UNIQUE, INDEX, NOT NULL |
| name | String(100) | NOT NULL |
| description | Text | NOT NULL, default "" |

**Values:** head/Голова, shell/Панцирь, whirlwind/Вихрь, ghost/Призрак

**Relationships:** Reference table — no FK references to it (archetype_code is stored as string elsewhere)

---

## 7. `clans`
**Model:** `Clan` — Leader-created clans for team competition.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| owner_id | UUID | FK → users.id, NOT NULL |
| name | String(255) | NOT NULL |

**Relationships:**
- Clan → User: owner_id (many-to-one)
- One-to-many: Clan → ClanMember

---

## 8. `clan_members`
**Model:** `ClanMember` — Membership of a user in a clan.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| user_id | UUID | FK → users.id, UNIQUE, NOT NULL |
| clan_id | UUID | FK → clans.id, NOT NULL |

**Relationships:**
- ClanMember → User: user_id (many-to-one, one-to-one)
- ClanMember → Clan: clan_id (many-to-one)

---

## 9. `groups`
**Model:** `Group` — Mentor groups (curator, leader, specialist).

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| owner_id | UUID | FK → users.id, NOT NULL |
| type | String(50) | NOT NULL (curator/leader/specialist) |
| name | String(255) | NOT NULL |
| max_members | Integer | default 10 |

**Relationships:**
- Group → User: owner_id (many-to-one)
- One-to-many: Group → User (via users.group_id)

---

## 10. `user_completions`
**Model:** `UserCompletion` — Quest completion with XP and streak tracking.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, NOT NULL |
| scroll_id | UUID | FK → scrolls.id, NOT NULL |
| completed_at | DateTime(tz) | server_default now() |
| xp_awarded | Integer | default 10 |
| report_text | Text | nullable |
| report_media_url | String(255) | nullable |
| report_media_type | String(20) | nullable |

**Constraints:** UNIQUE(user_id, scroll_id)

**Relationships:**
- UserCompletion → User: user_id (many-to-one)
- UserCompletion → Scroll: scroll_id (many-to-one)

---

## 11. `daily_scrolls`
**Model:** `DailyScroll` — Scroll content for each day + scroll_type combination.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| day_number | Integer | NOT NULL, INDEX |
| scroll_type_id | UUID | FK → scroll_types.id, INDEX, NOT NULL |
| title | String(200) | NOT NULL, default "" |
| content | Text | NOT NULL, default "" |
| media_file_id | String(200) | nullable |
| published_at | DateTime(tz) | nullable |

**Constraints:** UNIQUE(day_number, scroll_type_id)

**Relationships:**
- DailyScroll → ScrollType: scroll_type_id (many-to-one)
- Referenced by: UserDailyCommand.daily_scroll_id

---

## 12. `user_daily_commands`
**Model:** `UserDailyCommand` — Tracks which commands a user has completed each day.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| user_id | UUID | FK → users.id, INDEX, NOT NULL |
| quest_day | Integer | NOT NULL, INDEX |
| command | String(30) | NOT NULL |
| slot | String(20) | NOT NULL, default "" |
| scroll_type_id | UUID | FK → scroll_types.id, nullable |
| daily_scroll_id | UUID | FK → daily_scrolls.id, nullable |
| xp_awarded | Integer | NOT NULL, default 0 |
| completed_at | DateTime(tz) | NOT NULL |
| report_text | Text | nullable |
| report_media_url | String(300) | nullable |
| report_media_type | String(20) | nullable |

**Constraints:** UNIQUE(user_id, quest_day, command, slot)

**Relationships:**
- UserDailyCommand → User: user_id (many-to-one)
- UserDailyCommand → ScrollType: scroll_type_id (many-to-one, nullable)
- UserDailyCommand → DailyScroll: daily_scroll_id (many-to-one, nullable)

---

## 13. `role_history`
**Model:** `RoleHistory` — Audit log for role changes.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| user_id | UUID | FK → users.id, INDEX, NOT NULL |
| old_role | String(50) | NOT NULL |
| new_role | String(50) | NOT NULL |
| changed_by_id | UUID | FK → users.id, nullable |

**Relationships:**
- RoleHistory → User: user_id (many-to-one)
- RoleHistory → User: changed_by_id (many-to-one, nullable)

---

## 14. `payments`
**Model:** `Payment` — Platega.io payment transactions.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| user_id | UUID | FK → users.id, NOT NULL |
| platega_transaction_id | String(255) | UNIQUE, nullable |
| amount | Integer | NOT NULL (kopecks) |
| currency | String(3) | default "RUB" |
| status | String(50) | default "pending" |
| payment_method | String(50) | nullable |
| idempotency_key | String(255) | UNIQUE, nullable |

**Relationships:**
- Payment → User: user_id (many-to-one)

---

## 15. `commission_balances`
**Model:** `CommissionBalance` — Mentor commission tracking.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| user_id | UUID | FK → users.id, UNIQUE, INDEX, NOT NULL |
| total_earned | Integer | default 0 (kopecks) |
| total_pending | Integer | default 0 (kopecks) |
| total_paid_out | Integer | default 0 (kopecks) |
| last_commission_at | DateTime(tz) | nullable |

**Relationships:**
- CommissionBalance → User: user_id (one-to-one)

---

## 16. `prize_funds`
**Model:** `PrizeFund` — Prize fund pool for distributing rewards.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| name | String(255) | NOT NULL |
| total_amount | Integer | default 0 (kopecks) |
| percent_rule | String(20) | default "xp" (xp/streak/custom) |
| status | String(20) | default "open" (open/distributed) |
| distributed_at | DateTime(tz) | nullable |

**Relationships:**
- One-to-many: PrizeFund → PrizeFundPayout

---

## 17. `prize_fund_payouts`
**Model:** `PrizeFundPayout` — Individual payout from a prize fund.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| prize_fund_id | UUID | FK → prize_funds.id, INDEX, NOT NULL |
| user_id | UUID | FK → users.id, NOT NULL |
| amount | Integer | NOT NULL (kopecks) |
| paid_at | DateTime(tz) | nullable |

**Relationships:**
- PrizeFundPayout → PrizeFund: prize_fund_id (many-to-one)
- PrizeFundPayout → User: user_id (many-to-one)

---

## 18. `notifications`
**Model:** `Notification` — Queued notifications for users.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| user_id | UUID | FK → users.id, INDEX, nullable |
| type | String(50) | NOT NULL (scroll_reminder/streak_warning/system/broadcast) |
| payload | Text | NOT NULL, default "" |
| sent_at | DateTime(tz) | nullable |
| media_url | String(500) | nullable |
| media_type | String(20) | nullable (photo/video/document) |
| scheduled_at | DateTime(tz) | nullable, INDEX |
| audience | String(20) | nullable (archetype or "all") |
| parse_mode | String(10) | nullable (HTML/Markdown) |

**Relationships:**
- Notification → User: user_id (many-to-one, nullable for broadcasts)

---

## 19. `moderation_reports`
**Model:** `ModerationReport` — Player complaints and moderation actions.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| user_id | UUID | FK → users.id, INDEX, NOT NULL |
| reason | Text | NOT NULL |
| status | String(20) | NOT NULL, default "pending" (pending/warned/banned/excluded) |

**Relationships:**
- ModerationReport → User: user_id (many-to-one)

---

## 20. `settings`
**Model:** `Setting` — Key-value platform configuration.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| key | String(100) | UNIQUE, NOT NULL |
| value | Text | NOT NULL |

**Relationships:** None (standalone key-value store)

---

## 21. `audit_log`
**Model:** `AuditLog` — Append-only admin action history.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| admin_id | UUID | FK → users.id, nullable |
| action | String(100) | NOT NULL |
| details | Text | nullable |
| created_at | DateTime(tz) | server_default now() |

**Note:** No `updated_at` — audit logs are append-only, never modified.

**Relationships:**
- AuditLog → User: admin_id (many-to-one, nullable)

---

## Entity Relationship Summary

```
User (users)
 ├── referrals (referrer_id, referee_id)
 ├── groups (group_id → groups.id)
 ├── clans (clan_id → clans.id)
 ├── clan_members (user_id, clan_id)
 ├── user_completions (user_id, scroll_id → scrolls.id)
 ├── user_daily_commands (user_id, scroll_type_id, daily_scroll_id)
 ├── role_history (user_id, changed_by_id)
 ├── payments (user_id)
 ├── commission_balances (user_id, one-to-one)
 ├── prize_fund_payouts (user_id)
 ├── notifications (user_id)
 ├── moderation_reports (user_id)
 ├── audit_log (admin_id)
 └── scroll_archetype_tasks (via scroll_id)

Scroll (scrolls)
 ├── scroll_archetype_tasks (scroll_id)
 └── user_completions (scroll_id)

ScrollType (scroll_types)
 ├── daily_scrolls (scroll_type_id)
 └── user_daily_commands (scroll_type_id)

DailyScroll (daily_scrolls)
 ├── user_daily_commands (daily_scroll_id)
 └── scroll_types (scroll_type_id)

Clan (clans)
 └── clan_members (clan_id)

Group (groups)
 └── users (group_id)

PrizeFund (prize_funds)
 └── prize_fund_payouts (prize_fund_id)

Archetype (archetypes)
 └── reference only (codes used as strings in users.archetype, scroll_archetype_tasks.archetype_code)

Setting (settings)
 └── standalone KV store
```

**Total: 21 tables, ~100 columns, ~30 foreign key relationships.**
