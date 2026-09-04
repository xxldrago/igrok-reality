# Domain Pitfalls

**Domain:** Telegram bot platform with scheduled content delivery, payments, and gamification
**Researched:** 2026-09-04
**Overall confidence:** HIGH (official Telegram docs + production experience reports)

## Critical Pitfalls

Mistakes that cause rewrites, user loss, or platform bans.

### Pitfall 1: 08:00 Morning Blast — The Rate Limit Time Bomb

**What goes wrong:** At 08:00, the scheduler fires 500+ identical messages simultaneously. Telegram's Bot API enforces strict rate limits: ~30 messages/second across different chats, ~20 messages/minute to the same channel. Violating these returns HTTP 429 with `retry_after`. If you ignore 429s, Telegram escalates backoff and may temporarily ban the bot token. Sustained ignoring gets you in front of Telegram's platform team.

**Why it happens:** Developers treat "scheduled at 08:00" as "all delivered at 08:00." They don't account for Telegram's per-scope limits or assume the library handles it automatically — most libraries react to 429 after the fact, not proactively.

**Consequences:**
- 100+ messages fail on launch morning, players see nothing
- Telegram imposes exponential backoff, delaying subsequent deliveries
- Worst case: bot token temporarily disabled, quest platform is dead for the day
- Players who don't receive morning Свиток disengage permanently

**Prevention:**
- Implement token-bucket rate limiting per scope: 30 tokens/sec global, 1 token/sec per chat
- Stagger deliveries across 08:00–12:00 (2-minute spacing between same-destination messages)
- Use `sendMediaGroup` for batching (1 API call = up to 10 items)
- Monitor 429 counter per minute; alert on any sustained increase
- Consider separate bot tokens for broadcast vs. interactive traffic

**Detection:** Morning delivery shows <90% success rate; 429 errors in logs; users report missing Свитки

**Phase:** Core (Phase 3 — daily delivery)

### Pitfall 2: Payment Webhook — The Silent Double-Spend

**What goes wrong:** Payment providers (YooKassa, CloudPayments) send webhooks over HTTP. Networks retry. You WILL receive the same `successful_payment` / webhook twice. Without idempotent handling, you grant access twice, charge twice, or trigger duplicate commission calculations.

**Why it happens:** Developers treat webhooks as fire-and-forget. They don't persist a unique payment ID and check for duplicates. Or they do the check in-memory (lost on restart) instead of the database.

**Consequences:**
- Player pays once but receives access twice (revenue leak)
- Commission calculated on duplicate payment (financial inaccuracy)
- Refund logic breaks because system thinks two payments exist
- Audit trail becomes unreliable

**Prevention:**
- Store payment's unique ID (`payment_id` or `invoice_payload`) in database BEFORE processing
- Use database unique constraint + upsert pattern: `INSERT ... ON CONFLICT DO NOTHING`
- Process webhook in transaction: check idempotency → grant access → log, all in one DB transaction
- Never grant access based on Telegram message alone — always persist order state (`pending → paid → fulfilled`)

**Detection:** Duplicate entries in payment logs; users reporting "I was charged twice"; commission amounts don't match revenue

**Phase:** Core (Phase 2 — payments)

### Pitfall 3: pre_checkout_query Timeout — The 10-Second Trap

**What goes wrong:** Telegram sends `pre_checkout_query` when user presses "Pay." You have exactly 10 seconds to call `answerPreCheckoutQuery(ok=true)`. If you don't respond in time, the transaction is canceled — even though the user did nothing wrong. The user sees "payment error" and blames your bot.

**Why it happens:** Developer validates price, checks inventory, verifies user permissions inside the pre_checkout handler. Any DB query, external API call, or slow logic pushes you past 10 seconds.

**Consequences:**
- User sees "Payment failed" despite entering correct card details
- Abandoned checkout = lost revenue
- Repeated failures = user never returns to pay
- Support tickets about "bot doesn't work"

**Prevention:**
- Keep pre_checkout validation lightweight: read from cache/Redis, not complex DB queries
- If validation requires slow checks, pre-validate on invoice creation (cache the result)
- Implement anti-spam: rate-limit invoices per user (1 per 60 seconds)
- Log every `pre_checkout_query` ID for debugging failures
- Handle errors gracefully: return `answerPreCheckoutQuery(false, "human-readable reason")` instead of timing out

**Detection:** Payment failure rate > 5%; users reporting "payment error" on Telegram

**Phase:** Core (Phase 2 — payments)

### Pitfall 4: Streak System — The Burnout Engine

**What goes wrong:** Streak mechanics shift from motivation (accomplishment) to anxiety (loss avoidance) around day 30. Users with 47-day streaks who miss one day don't restart — they quit. The psychological response to seeing a zero-day counter after months of effort is shame and abandonment, not renewed motivation.

**Why it happens:** Developers design streaks for the ideal user (consistent, never misses). Real users have jobs, get sick, travel. Hard resets at the exact moment of lapse punish loyalty instead of rewarding recovery.

**Consequences:**
- Your most engaged users burn out and leave first (they invested the most)
- Streak anxiety creates negative association with the product
- Broken streaks suppress engagement below baseline (Silverman & Barasch, 2023)
- Users report the product feels "exhausting" or "too much effort"

**Prevention:**
- Build Grace Periods from day one: allow 1 missed day per month without losing streak
- Implement Recovery Quests: short challenge that restores broken streak (preserves dignity)
- Use 7-day capped cycles instead of infinite counters (psychological weight never exceeds 7 days)
- Transition from daily pressure to permanent status recognition at day 30+
- Never monetize streak anxiety (the Duolingo trap — works short-term, erodes trust long-term)

**Detection:** Day 30+ retention drops; users complaining about "streak pressure"; engagement metrics look strong but Day 7/30 retention is falling

**Phase:** Gamification (Phase 4 — XP, streaks, clans)

### Pitfall 5: Timezone Chaos — The 03:00 Notification

**What goes wrong:** Bot sends daily Свиток at "08:00" using server timezone. Players in different Russian timezones (and Russia spans 11!) receive notifications at 3 AM, 5 AM, or during sleeping hours. Players block the bot. Complaint rate rises. Telegram downgrades message delivery.

**Why it happens:** Developer uses server-local time or assumes all users are in Moscow timezone. Doesn't collect timezone on registration. Doesn't segment by timezone before scheduling.

**Consequences:**
- Players blocked from sleep-time notifications
- Telegram's implicit risk control flags high block rate → bot downgraded
- Higher complaint rate → bot faces ban risk
- Low engagement on Свитки sent at wrong time

**Prevention:**
- Collect timezone during registration (or infer from Telegram user locale)
- Segment users by timezone, schedule separate delivery windows per segment
- Default to UTC+3 (Moscow) if timezone unknown, with `/timezone` command for adjustment
- Test with sample users in different timezones before launch
- Monitor block rate per timezone segment after each broadcast

**Detection:** High bot-block rate in specific regions; users complaining about notification timing

**Phase:** Core (Phase 3 — daily delivery)

### Pitfall 6: Webhook Not Idempotent — The Duplicate Delivery

**What goes wrong:** Telegram webhook delivery is at-least-once. Your server processes the update, grants access, but crashes before returning 200 OK to Telegram. Telegram retries. You process the same update twice. Duplicate messages sent, duplicate XP awarded, duplicate access granted.

**Why it happens:** Developer processes webhook synchronously without idempotency checks. Returns 200 OK only after full processing (slow). Or doesn't use `update_id` as idempotency key.

**Consequences:**
- User receives same Свиток twice in one day
- XP and streak counted twice
- Bot appears unreliable to users
- Audit trail corrupted with duplicate entries

**Prevention:**
- Return 200 OK immediately, process asynchronously via queue (ARQ/Redis)
- Use `update_id` as idempotency key: `INSERT INTO processed_updates (update_id) ON CONFLICT DO NOTHING`
- If processing fails, log and alert — don't retry automatically without deduplication
- Design all handlers as idempotent: processing the same update twice produces the same result

**Detection:** Duplicate messages in chat; duplicate XP entries; "I got the same Свиток twice"

**Phase:** Core (Phase 1 — bot foundation)

## Moderate Pitfalls

Issues that cause technical debt, user confusion, or operational overhead.

### Pitfall 7: Channel Invite Link Expiry — The Access Revocation Nightmare

**What goes wrong:** One-time invite links to the private channel expire or get used up. New paying players can't join. Players who reinstalled Telegram lose access. No automatic re-invitation mechanism exists.

**Why it happens:** Developer generates invite link once at payment time. Doesn't track link validity or handle link exhaustion.

**Consequences:**
- Paying players can't access content → refund requests
- Manual intervention required for every access issue
- Players who change devices lose access permanently

**Prevention:**
- Store invite link per player in database, track expiry date
- Implement auto-regeneration when link is near expiry or exhausted
- Provide `/revoke_access` command that generates fresh link
- Monitor link usage vs. player count daily
- Consider permanent member links with revoke capability for problematic users

**Detection:** Support tickets about "can't access channel"; player count in channel < paid player count

**Phase:** Core (Phase 2 — payments & access)

### Pitfall 8: Missing Unsubscribe Mechanism — The Ban Risk

**What goes wrong:** Bot sends daily messages with no way to opt out. Users who want to stop receiving messages have only two options: block the bot or report it. Both increase Telegram's spam metrics. Telegram's implicit risk control downgrades or bans bots with high complaint rates.

**Why it happens:** Developer assumes "they paid for the quest, so they want messages." Doesn't consider that some players will want to pause, skip days, or leave early.

**Consequences:**
- High block rate → Telegram downgrades bot delivery
- Bot may be temporarily disabled
- No way to re-engage users who blocked out of frustration
- Legal risk under 152-FZ (Russian data protection) if no consent withdrawal mechanism

**Prevention:**
- Implement `/unsubscribe` and `/stop` commands
- Include "Reply /unsubscribe to pause notifications" in every broadcast
- Unsubscribe should pause, not delete (allow re-subscription)
- Monitor block rate per segment; reduce frequency if rate spikes
- Add unsubscribe prompt to initial onboarding

**Detection:** Rising block rate; users reporting "can't stop notifications"; Telegram warning about spam

**Phase:** Core (Phase 3 — daily delivery)

### Pitfall 9: Gamification Without Social Context — The Empty Leaderboard

**What goes wrong:** Global leaderboard with 500+ players. Top 10 are always the same no-lifers. Everyone else ignores it. Leaderboard gets high launch-day engagement, then drops to <10% returning viewers within 2-4 weeks.

**Why it happens:** Developer implements generic leaderboard without social units. Doesn't scope to meaningful groups (clans, cohorts, friends). Assumes competition drives engagement universally.

**Consequences:**
- Leaderboard feature becomes dead weight
- Players feel "the game isn't for me" → disengage
- Development time wasted on unused feature
- Misleading engagement metrics (high initial views, low retention)

**Prevention:**
- Scope leaderboards to clans (already planned in PROJECT.md — use this!)
- Show "Top 10 in your clan" not "Top 10 globally"
- Add "Your rank among friends" if social graph exists
- Make leaderboard opt-in, not mandatory
- Track returning-user rate on leaderboard view; if <10% after 2 weeks, redesign

**Detection:** Leaderboard view rate drops below 10% after launch; players not mentioning leaderboard in feedback

**Phase:** Gamification (Phase 4 — XP, streaks, clans)

### Pitfall 10: Hardcoded Gamification Values — The Ship-and-Forget Trap

**What goes wrong:** XP rewards, level curves, quest difficulty, streak rules are hardcoded in source code. Changing any value requires code deploy. Team ships gamification, sees small bump, moves on. Values are never tuned. System regresses within a year.

**Why it happens:** Developer treats gamification as a feature to ship, not a system to maintain. Hardcodes values for simplicity. Doesn't build analytics or iteration cadence.

**Consequences:**
- XP system becomes meaningless (too easy/hard to level up)
- Quest completion rates drift without anyone noticing
- Wrong behaviors get amplified (gamifying activity instead of outcome)
- System becomes "dead weight" that nobody knows how to modify

**Prevention:**
- Store all gamification parameters in database (not code): XP per action, level thresholds, quest difficulty
- Build admin interface for tuning values without deploy
- Instrument every mechanic: completion rates, drop-off points, earned-by percentage
- Establish iteration cadence: review gamification metrics every 2 weeks
- Set thresholds: achievements earned by <5% = too hard, >95% = trivial

**Detection:** Gamification metrics not reviewed in > 2 weeks; XP values same as launch; quest completion rates untracked

**Phase:** Gamification (Phase 4 — XP, streaks, clans)

### Pitfall 11: Payment Currency/Amount Mismatch — The "Payment Error" Message

**What goes wrong:** Telegram invoice shows price in rubles, but code sends amount in kopecks (×100 mismatch). Or currency code doesn't match provider's expected format. User sees "Payment processing error" — the most common Telegram payment error.

**Why it happens:** YooKassa/CloudPayments expect amounts in kopecks. Telegram's invoice format has specific currency requirements. Developer mixes up units or uses wrong currency code.

**Consequences:**
- Every payment attempt fails with cryptic error
- Users can't pay → zero revenue
- Debugging takes hours because error message is generic
- First impression of payment system is "broken"

**Prevention:**
- Store prices in kopecks internally (never convert at runtime)
- Validate currency is "RUB" (not "RUR" or "USD")
- Test full payment flow in sandbox before going live (YooKassa and CloudPayments both have test modes)
- Log exact invoice payload sent to Telegram for debugging
- Handle `pre_checkout_query` errors with human-readable reasons

**Detection:** 100% payment failure rate on first day; users reporting "payment error" immediately

**Phase:** Core (Phase 2 — payments)

## Minor Pitfalls

Issues that cause inconvenience, technical debt, or suboptimal UX.

### Pitfall 12: Media Storage in Telegram — The file_id Rot

**What goes wrong:** Свитки reference Telegram `file_id` for media. If Telegram deletes the file (rare but possible), or bot is recreated, or file_id format changes, all media references break. Свитки show empty or error.

**Why it happens:** Developer assumes Telegram file_ids are permanent. Doesn't implement backup storage.

**Consequences:**
- Свитки with media break silently
- No way to recover without re-uploading all media
- Historical content becomes inaccessible

**Prevention:**
- Implement dual storage: Telegram file_id + S3 backup (as decided in PROJECT.md)
- On upload, save to both Telegram and S3 simultaneously
- On send, try file_id first; fall back to S3 if Telegram returns error
- Periodic audit: verify all file_ids still resolve

**Detection:** Свитки showing empty media; file_id resolution errors in logs

**Phase:** Content (Phase 3 — Свитки system)

### Pitfall 13: No Admin Audit Trail — The "Who Did What?" Problem

**What goes wrong:** Мастер changes quest rules, adjusts payments, modifies user access. No log of who did what when. Discrepancies appear. Nobody can explain why. Financial reconciliation becomes impossible.

**Why it happens:** Developer focuses on user-facing features, neglects admin operations logging. Assumes "I'll remember" or "it's just me."

**Consequences:**
- Financial disputes with no audit trail
- accidental changes with no rollback capability
- Compliance issues under 152-FZ (data protection audit requirements)
- Onboarding new admins is impossible without documentation

**Prevention:**
- Log every Мастер action: who, what, when, before/after values
- Store in append-only audit table (never UPDATE audit logs)
- Include audit in web admin interface (filterable by action type, user, date)
- Make audit logs immutable and exportable

**Detection:** Discrepancies in financial data; inability to explain access changes; compliance audit fails

**Phase:** Admin (Phase 5 — web admin)

### Pitfall 14: Long Polling in Production — The Latency Trap

**What goes wrong:** Developer uses `getUpdates` (long polling) in production. Bot has 30-60 second delay on responses. Users perceive bot as slow. Under load, long polling causes connection exhaustion and missed updates.

**Why it happens:** Long polling works great in development (simpler, no HTTPS setup). Developer forgets to switch to webhooks for production.

**Consequences:**
- 30-60 second response delay frustrates users
- Under load, updates are missed or delayed
- Server resources wasted on persistent connections
- Doesn't scale beyond single process

**Prevention:**
- Use webhooks for production (as planned in PROJECT.md)
- Set up HTTPS endpoint with valid certificate
- Return 200 OK immediately, process asynchronously
- Implement proper webhook secret token verification
- Test webhook reliability under load before launch

**Detection:** Bot feels slow; updates occasionally missing; server resource usage high

**Phase:** Core (Phase 1 — bot foundation)

### Pitfall 15: No Refund Flow — The Support Nightmare

**What goes wrong:** Player pays but wants refund. No automated refund mechanism. Admin must manually process refund via payment provider dashboard, then manually revoke access in bot. Process is slow, error-prone, and doesn't scale.

**Why it happens:** Developer implements payment flow but not the reverse. Assumes "nobody will request refunds."

**Consequences:**
- Refund requests pile up in support queue
- Manual processing takes hours/days
- Access revocation often forgotten → player keeps access after refund
- Revenue reconciliation becomes nightmare

**Prevention:**
- Implement `/refund` admin command that triggers provider API refund
- Refund handler must: process refund → revoke channel access → log refund → notify player
- Store refund status in payment record (linked to original payment)
- Test refund flow in sandbox before launch
- Set clear refund policy in Terms of Service (Telegram requires this)

**Detection:** Refund requests taking > 24 hours; manual refund processing; access not revoked after refund

**Phase:** Core (Phase 2 — payments)

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| Phase 1: Bot foundation | Long polling in production; webhook setup errors | Use webhooks from day one; test with real Telegram client |
| Phase 2: Payments | pre_checkout timeout; idempotent webhooks; currency mismatch | Sandbox testing; idempotency keys; amount validation |
| Phase 3: Daily delivery | Rate limit blast at 08:00; timezone chaos; missing unsubscribe | Token-bucket rate limiter; timezone segmentation; /stop command |
| Phase 4: Gamification | Streak burnout; empty leaderboards; hardcoded values | Grace periods; clan-scoped boards; database-stored config |
| Phase 5: Admin | No audit trail; manual refund nightmare | Append-only audit logs; automated refund flow |
| Phase 6: Clans | Clan leaderboard scope; aggregate progress calculation | Test with multiple clans; handle edge cases (empty clans) |

## Sources

- Telegram Bot API FAQ (core.telegram.org/bots/faq) — official rate limits and payment docs
- Telegram Bot Payments API (core.telegram.org/bots/payments/) — pre_checkout_query, webhook requirements
- Autogram: Telegram Bot API Rate Limits 2026 — practical rate limit strategies
- grammY: Scaling Up IV: Flood Limits — production rate limit patterns
- DEV Community: Building a Telegram bot that takes payments — idempotent payment processing
- Yu-kai Chou: Streak Design — gamification psychology and burnout research
- Mind the Product: Why gamification kills products — overjustification effect and retention
- EngageFabric: 5 Gamification Anti-Patterns — common gamification mistakes
- TG-Staff: Complete Guide to Scheduled Mass Messages — timezone and frequency strategies
- Silverman & Barasch (2023): Broken streaks suppress engagement below baseline
