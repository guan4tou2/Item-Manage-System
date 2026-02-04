# Home Expiry & Location UX Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve household use by surfacing expiry risk early and making locations faster to enter and find.

**Architecture:** Reuse existing `item_service` expiry annotations and `get_notification_count`, extend `items` routes to expose expiry/near-expiry datasets, and adjust templates for dashboard/search UX. Keep storage schema unchanged; add small helpers for recent locations and default purchase/expiry presets. 

**Tech Stack:** Flask blueprints, Jinja templates (`home.html`, `search.html`), services in `app/items/routes.py`, `app/services/item_service.py`, tests in `tests/` (pytest).

---

### Task 1: Dashboard shows expiry-at-a-glance cards

**Files:**
- Modify: `app/items/routes.py` (home route to supply expiry stats/lists)
- Modify: `templates/home.html` (cards for expired/near, quick actions link)
- Test: `tests/test_notifications.py` (add view-level check)

**Step 1: Write the failing test**
- Add pytest to request home (`client.get('/')`) and assert JSON context has `expired_count`/`near_count` or rendered text shows counts.

**Step 2: Run test to verify it fails**
- Run: `python -m pytest tests/test_notifications.py -k home_dashboard -v`
- Expect fail: missing fields/content.

**Step 3: Implement route support**
- In `app/items/routes.py`, extend home handler to call `item_service.get_notification_count()` and pass counts plus `expired`/`near_expiry` snippets (top 3 each) to the template.

**Step 4: Implement template cards**
- In `templates/home.html`, add two cards (Expired / 30-day Near), showing counts and a button linking to `url_for('items.expiry')` or search filtered by expiry. Render top 3 items with name + location + date.

**Step 5: Run tests**
- Run: `python -m pytest tests/test_notifications.py -k home_dashboard -v`
- Expect pass.

---

### Task 2: Search defaults to earliest expiry and adds “has expiry” filter

**Files:**
- Modify: `app/items/routes.py` (search handler to default sort=earliest expiry; optional filter `has_expiry`)
- Modify: `app/services/item_service.py` (honor `sort=expiry` mapping to earliest of Usage/Warranty; apply `has_expiry` filter)
- Modify: `templates/search.html` (UI controls: sort dropdown default to earliest; checkbox/toggle for only items with expiry)
- Test: `tests/test_system.py` or new `tests/test_search.py` (search respects sort/filter)

**Step 1: Write failing tests**
- Add tests that create items with different Usage/Warranty dates and assert search results order by earliest expiry when no sort specified, and that `has_expiry=1` excludes items with no dates.

**Step 2: Run tests to see them fail**
- Run: `python -m pytest tests/test_system.py -k expiry_search -v`

**Step 3: Implement service + route changes**
- In `item_service.list_items`, support sort option `expiry` (earliest of Usage/Warranty) and optional filter `has_expiry`.
- In search route, set default sort to `expiry` and pass filter flag from query.

**Step 4: Update template controls**
- Default sort dropdown selection to earliest expiry; add toggle/checkbox “只顯示有到期日”.

**Step 5: Run tests**
- Run: `python -m pytest tests/test_system.py -k expiry_search -v`

---

### Task 3: Quick location presets and copy-friendly display

**Files:**
- Modify: `app/items/routes.py` (add helper to fetch last 5 locations across items; include in add/edit context)
- Modify: `app/services/location_service.py` (new method to list recent locations from items’ `ItemStorePlace`/Floor/Room/Zone` aggregates)
- Modify: `templates/additem.html`, `templates/edititem.html`, `templates/home.html` or `search.html` (render quick-pick buttons and copy-to-clipboard for location string)
- Test: `tests/test_system.py` or new `tests/test_locations.py` (recent locations surfaced; copy text appears)

**Step 1: Write failing tests**
- Add tests ensuring add/edit pages include recent locations list and that recent list pulls from latest items.

**Step 2: Run tests to see failure**
- Run: `python -m pytest tests/test_locations.py -k recent_locations -v`

**Step 3: Implement services/routes**
- In location service, aggregate last N non-empty locations ordered by latest `move_history` or creation; return unique list.
- In routes, inject `recent_locations` into add/edit templates; expose combined location string for copy.

**Step 4: Update templates**
- Add “常用位置” pills/buttons to prefill fields; add a copy icon/button near displayed location on home/search cards.

**Step 5: Run tests**
- Run: `python -m pytest tests/test_locations.py -k recent_locations -v`

---

**Execution Note:** After plan approval, use `superpowers:executing-plans` to drive implementation task-by-task with tests before template changes where applicable.
