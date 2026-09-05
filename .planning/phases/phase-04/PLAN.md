# Phase 4: User Progress — Master Plan

## Goal

Users see their completion streaks, XP, and leaderboard position.

## Requirement IDs

COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, COMP-07

## Success Criteria

1. User taps completion button and receives XP confirmation
2. Streak counter increments on completion and resets on miss
3. Streak calculation respects user's local timezone
4. Leaderboard shows ranked users by XP/streak
5. Leaderboard updates in real-time after completions

## Wave Structure

| Wave | Plans | Parallel? |
|------|-------|-----------|
| 1 | 04-01 | — |
| 2 | 04-02, 04-03 | Yes (no file overlap) |

## Plans

- [ ] `04-01-PLAN.md` — Progress service layer, completion callback wiring, XP awards, leaderboard Redis write (Wave 1)
- [ ] `04-02-PLAN.md` — Streak tracking with timezone-aware calculations (Wave 2)
- [ ] `04-03-PLAN.md` — Leaderboard display, /progress and /leaderboard commands (Wave 2)
