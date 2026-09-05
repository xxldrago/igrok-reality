---
phase: phase-07
type: execute
plans: 4
waves: 3
requirements: [ADM-01, ADM-02, ADM-03, ADM-04, ADM-05, ADM-06, ADM-07, ADM-08]

# Wave structure
# Wave 1: 07-01 (React app scaffolding + JWT auth + routing)
# Wave 2: 07-02 (User management) + 07-03 (Scroll CRUD + payments) [parallel]
# Wave 3: 07-04 (Settings, audit log, role-based access)

must_haves:
  truths:
    - "Admin can log in with credentials and receives JWT token"
    - "Admin can search and filter user list by name, archetype, status"
    - "Admin can view detailed user profiles"
    - "Admin can create, edit, and delete scrolls"
    - "Admin can view payment list and details"
    - "Admin can configure platform settings (key-value pairs)"
    - "All admin actions are logged in audit trail"
    - "Admin authentication restricts access to authorized roles (master/leader/curator)"
  artifacts:
    - src/admin/               # React application (scaffolded with Vite + Ant Design)
    - src/app/api/auth.py      # JWT authentication module
    - src/app/api/routes/admin.py  # Expanded admin API endpoints
    - src/app/api/dependencies.py  # FastAPI dependencies (get_current_user, require_role)
  key_links:
    - "JWT login -> token -> React auth context -> protected routes"
    - "Admin API endpoints -> auth dependency -> role check"
    - "Frontend pages -> API client -> backend endpoints"
    - "All mutations -> AuditLog creation"
---

# Phase 7: Admin Panel — Plan

**Goal: Leaders and masters can manage all platform operations**

## User Story

**As a** master or leader managing the quest platform,
**I want** a web-based admin panel to manage users, scrolls, payments, and settings,
**so that** I can oversee all platform operations without using database queries or bot commands.

## Plan Overview

| Plan | Name | Wave | Depends On | Requirements |
|------|------|------|------------|--------------|
| 07-01 | React app scaffolding, JWT auth, routing | 1 | — | ADM-08 |
| 07-02 | User management (list, search, details) | 2 | 07-01 | ADM-01, ADM-02 |
| 07-03 | Scroll CRUD, payment management | 2 | 07-01 | ADM-03, ADM-04, ADM-05 |
| 07-04 | Settings, audit log, role-based access | 3 | 07-01 | ADM-06, ADM-07 |

## Wave Execution

### Wave 1
- **07-01**: React + Vite + Ant Design scaffolding, JWT auth backend + frontend, routing, login page

### Wave 2 (parallel)
- **07-02**: User list with search/filter/pagination, user detail view
- **07-03**: Scroll CRUD (list/create/edit/delete), payment list and detail views

### Wave 3
- **07-04**: Settings key-value editor, audit log viewer, role-based UI guards

## Success Criteria

1. Admin can log in at /login and receives a JWT token
2. Admin can search and filter user list by name, username, telegram_id, archetype, status
3. Admin can view detailed user profiles with XP, streak, payments, completions
4. Admin can create, edit, and delete scrolls with day_number, archetype, text fields
5. Admin can view payment list filtered by status and user
6. Admin can configure platform settings as key-value pairs
7. All admin mutations create audit log entries with admin_id, action, timestamp
8. Non-admin users cannot access any /api/admin/* endpoints
9. Curators can only view data, leaders can manage users/scrolls, masters have full access

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| React + Ant Design 5 | User decision — fast admin UI development, rich component library |
| JWT tokens (not session cookies) | Stateless auth, works with SPA, simple to implement |
| Backend serves static files | Single origin for production, no CORS issues |
| FastAPI dependency injection for auth | Clean, testable, reusable across all endpoints |
| Key-value settings (not form-based) | Existing Setting model is key-value, keeps v1 simple |

## Dependencies from Prior Phases

- **Phase 1**: FastAPI app, database models (User, Scroll, Payment, AuditLog, Setting)
- **Phase 6**: Admin payout endpoints in src/app/api/routes/admin.py (existing)
- **Phase 1**: SQLAlchemy async session, Alembic migrations
- **All phases**: AuditLog model for action tracking

## Coverage Audit

| Requirement | Plan | Covered |
|-------------|------|---------|
| ADM-01 (User list with search/filter) | 07-02 | User list endpoint + frontend table |
| ADM-02 (User details) | 07-02 | User detail endpoint + frontend drawer |
| ADM-03 (Scroll CRUD) | 07-03 | Scroll list/create/update/delete endpoints + frontend |
| ADM-04 (Payments list) | 07-03 | Payment list endpoint + frontend table |
| ADM-05 (Payment details) | 07-03 | Payment detail endpoint + frontend |
| ADM-06 (Settings configuration) | 07-04 | Settings CRUD endpoint + frontend editor |
| ADM-07 (Audit log) | 07-04 | Audit log list endpoint + frontend table |
| ADM-08 (Admin authentication) | 07-01 | JWT login, auth middleware, role checks |

**All 8 requirements covered.** No gaps.
