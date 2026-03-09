# Project Audit And UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Audit the full Item Manage System user journey and ship the highest-value functional and UX improvements without changing the product scope.

**Architecture:** Use route-by-route auditing to validate the existing Flask app as a user would: authentication, item workflows, admin operations, notifications, import/export, and travel utilities. Fix the failures at the narrowest layer possible, then tighten the interface around those fixes so the improved flows are visible and easier to use.

**Tech Stack:** Flask, Jinja templates, SQLAlchemy/PyMongo compatibility layer, Bootstrap, vanilla JavaScript, Playwright MCP, unittest/pytest-style tests.

### Task 1: Audit Surface Inventory

**Files:**
- Modify: `docs/plans/2026-03-09-project-audit-and-ux-improvements.md`
- Inspect: `app/items/routes.py`
- Inspect: `app/auth/routes.py`
- Inspect: `app/notifications/routes.py`
- Inspect: `app/travel/routes.py`
- Inspect: `templates/`
- Inspect: `tests/`

**Step 1: List primary user flows**

Document these flows before changing code:
- Sign in and forced password change
- Browse/search/filter items
- Add/edit/delete item
- Favorites and quick actions
- Locations/types management
- Notifications and reorder
- Import/export/backup
- Travel list flow

**Step 2: Record coverage gaps**

Mark each flow with:
- Existing UI page
- Existing route/API
- Existing test coverage
- Known breakpoints from manual audit

### Task 2: Browser Flow Verification

**Files:**
- Inspect: `templates/home.html`
- Inspect: `templates/manageitem.html`
- Inspect: `templates/search.html`
- Inspect: `templates/locations.html`
- Inspect: `templates/template.html`

**Step 1: Run end-to-end checks**

Verify in desktop and mobile:
- Navbar and admin dropdown
- Home search/filter/scan
- Manage item table actions
- Add/edit forms
- Favorites page
- Notifications/reorder/statistics

**Step 2: Capture concrete failures**

Record only actionable failures such as:
- Route/API errors
- Broken state updates
- Hidden/ambiguous actions
- Layout breakpoints
- Missing affordances for common tasks

### Task 3: Fix Functional Breakpoints

**Files:**
- Modify: `app/items/routes.py`
- Modify: `app/services/item_service.py`
- Modify: `app/repositories/item_repo.py`
- Test: `tests/test_items.py`
- Test: `tests/test_routes.py`

**Step 1: Add or extend failing tests for discovered regressions**

Targets:
- Notification count payload consistency
- Favorites behavior
- Form/filter persistence where applicable
- Any route returning 4xx/5xx in valid user flows

**Step 2: Implement minimal backend fixes**

Patch only the layers causing the broken behavior. Keep API payloads consistent with the frontend.

### Task 4: Tighten UX Around High-Frequency Flows

**Files:**
- Modify: `templates/home.html`
- Modify: `templates/manageitem.html`
- Modify: `templates/search.html`
- Modify: `templates/locations.html`
- Modify: `templates/template.html`
- Modify: `static/css/main.css`
- Modify: `static/css/navbar.css`

**Step 1: Improve navigation clarity**

Focus on:
- Action grouping
- Mobile readability
- Repeated operations visibility
- Tooltip/dropdown consistency

**Step 2: Improve high-traffic pages**

Focus on:
- Search/filter comprehension
- Card/table action discoverability
- Empty states and section labels
- Visual spacing and hierarchy

### Task 5: Verification And Residual Risks

**Files:**
- Test: `tests/`
- Inspect: runtime pages via Playwright

**Step 1: Run code verification**

Run:
- `venv/bin/python -m py_compile app/items/routes.py app/services/item_service.py app/repositories/item_repo.py`

**Step 2: Re-run browser checks**

Confirm:
- No broken main flows
- No obvious overflow/offscreen elements
- Admin dropdown works on mobile
- Key counters and async widgets render without regressions

**Step 3: Summarize remaining gaps**

Call out anything not fixed in this pass, especially:
- Missing automated coverage
- Areas that still need deeper backend work
- Non-critical UX debt
