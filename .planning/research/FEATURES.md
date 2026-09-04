# Feature Landscape

**Domain:** Telegram-based quest/gamification platform (90-day challenge)
**Researched:** 2026-09-04
**Confidence:** HIGH

## Table Stakes

Features users expect in any Telegram quest platform. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Daily quest delivery** | Core value proposition — users expect content delivered automatically | Low | Telegram Bot API + scheduled messages. 20-25 msg/sec limit requires queuing |
| **Registration & onboarding** | Users must authenticate before participating | Low | Telegram-native auth (no extra forms). First message = start flow |
| **XP/points system** | Universal gamification primitive — every platform has it | Low | Simple counter per user. Consider daily caps to prevent spam |
| **Streak tracking** | #1 retention mechanic in Telegram bots (GM-Fi, StreakFarm) | Low | Reset on miss. Store by timezone, not server time |
| **Leaderboard/rankings** | Social comparison drives 30% more engagement | Low | Top-N display. Publish weekly in channel. Avoid full list (>100 users) |
| **Quest completion marking** | Users need to confirm they did the task | Low | Button tap + optional text/photo proof |
| **Payment processing** | Monetization requires it. Users expect Russian payment methods | Medium | ЮKassa/CloudPayments. Webhook + idempotency. PCI compliance |
| **Referral system** | Viral growth — every platform has it | Medium | Unique links. Track referrer. Reward both sides |
| **Notifications/reminders** | Users forget. Reminders bring back 40% of drop-offs | Low | Morning quest delivery + evening reminder. Queue-based |
| **Basic admin panel** | Master must manage content and users | Medium | React + Vite. CRUD for quests, users, payments |
| **Private channel access** | Paying users expect premium content gate | Low | One-time invite link. Track who has access |
| **Progress tracking** | Users want to see their journey | Low | XP total, streak length, quests completed |

## Differentiators

Features that set this platform apart from generic Telegram bots.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Archetype testing** | Personalization hook — 4 archetypes (Head, Shell, Whirlwind, Ghost) | Low | 4 questions → 4 outcomes. One-time test at registration |
| **Personalized quest delivery** | Archetype-based quest variants feel tailored | Medium | Same quest, different framing per archetype. Content duplication required |
| **Clan system** | Social accountability — teams of 3-100 players | High | Create/join/leave. Aggregated progress. Clan leaderboard |
| **Curator/Leader roles** | Mentor hierarchy scales to 500+ players | Medium | Curator (10 players), Leader (100 players), Specialist (extra quests) |
| **Prize fund** | Financial incentive drives completion | Medium | Configurable rules. Top N players split fund. Manual or automated |
| **Master's "Personal Path"** | Reports duplicated to private channel for review | Medium | Auto-forward text/photo/video submissions to Master's channel |
| **Mentor commission** | Multi-level reward system | Medium | Percentage from referrals' payments. Manual payout via admin |
| **90-day journey structure** | Finite commitment, not open-ended | Low | Fixed duration. Daily cadence. Clear start/end |
| **Archetype-specific quests** | Same task, different perspective per archetype | Medium | Content creator writes 4 variants or 1 universal + 3 flavor texts |
| **Web admin dashboard** | Professional management tool | High | React + Vite. Content, users, finances, moderation, settings, audit |
| **Audit trail** | Accountability for all Master actions | Low | Log who changed what and when. Simple append-only table |

## Anti-Features

Features to deliberately NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Mobile app** | Telegram-first — users won't install separate app | Use Telegram Mini Apps if UI complexity grows |
| **Microservices** | Overkill for 500 users. Adds deployment complexity | Modular monolith (bot, API, worker, scheduler as processes) |
| **Real-time player chat** | Not in TZ. Moderation nightmare. High cost | Players communicate via existing Telegram groups |
| **Video content in quests** | Storage/transfer expensive. Telegram file limits | Text + photos only. Video = Master's review channel only |
| **Multi-language support** | Only Russian audience. Adds translation burden | Single language (Russian) |
| **Automated mentor payouts** | Legal/compliance complexity | Manual payout via admin panel |
| **Blockchain/crypto integration** | TON adds complexity without value for this use case | Standard payment processors (ЮKassa/CloudPayments) |
| **AI-powered dynamic responses** | Over-engineering for 500 users. Unpredictable | Static quest content with archetype variants |
| **HTML5 mini-games** | Distracts from quest focus. Requires separate dev | Text-based quests with buttons, not games |
| **Complex branching storylines** | Content creation burden for 90 days × 4 archetypes | Linear daily quests with optional depth |
| **Social features (likes, comments)** | Moderation overhead. Not in TZ | Focus on individual progress + clan aggregation |
| **Achievement badges** | Nice-to-have but not in requirements. Add later | Post-MVP feature if retention data supports it |
| **Push notifications to groups** | Spam risk. Users mute noisy groups | Bot DM only for personal notifications |

## Feature Dependencies

```
Registration → Archetype Test → Private Channel Access → Daily Quest Delivery
                                          ↓
                                    Personalized Quests (archetype variants)
                                          ↓
                              Quest Completion → XP + Streak → Leaderboard
                                          ↓
                                    Reports (text/photo/video) → Master's Path
                                          ↓
                              Referral System → Mentor Commission → Prize Fund

Clan System → Clan Progress → Clan Leaderboard
                              ↓
                    Curator/Leader Roles → Mentor Commission

Payment Processing → Webhook → Access Grant → Commission Calculation
```

## MVP Recommendation

**Phase 1 — Core Loop (Ship fast, validate):**
1. Registration + archetype test
2. Daily quest delivery (text only)
3. Quest completion marking + XP/streak
4. Basic leaderboard
5. Payment processing + private channel access

**Phase 2 — Social & Growth:**
6. Referral system
7. Clan system
8. Curator/Leader roles
9. Mentor commission
10. Prize fund

**Phase 3 — Admin & Polish:**
11. Web admin dashboard (full)
12. Master's Personal Path
13. Audit trail
14. Notification queue (ARQ)

**Defer:**
- Achievement badges: Post-MVP. Add if retention data shows need
- Archetype quest variants: Start with universal quests, add variants in Phase 2
- Advanced analytics: Phase 3 if at all

## Sources

- GM-Fi Bot: streak mechanics, badge systems, leaderboards (gmfi.io)
- StreakFarm: daily check-ins, hourly boxes, referral tiers (github.com/streakfarm)
- Metricgram: points, rewards, streaks, anti-spam (metricgram.com)
- Telm: XP, levels, podium rankings (telm.com)
- ChatPlace: gamification templates, referral systems (chatplace.io)
- Activity platform: quest completion, points, referrals (tgram.link)
- DigitalOxygen: Telegram gamification mechanics overview (digitaloxy.ru)
- MemeFi Coin: clan mechanics, social collaboration (magnetto.com)
- Algoryte: Telegram game development challenges (algoryte.com)
- Telegram Bot API: rate limits, message types (core.telegram.org)
