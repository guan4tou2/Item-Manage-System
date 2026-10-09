# LINE + Telegram (LIFF Web-First) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the Web app as primary UI while adding LINE Official Account + Telegram bot for (1) expiry notifications and (2) convenient “open add/edit form” entrypoints with minimal friction.

**Architecture:** Add an “Integrations” layer: bind LINE userId / Telegram chatId to existing Web users via one-time binding codes; extend the existing notification scheduler to fan-out messages to Email/LINE/Telegram based on per-user preferences; provide LIFF entry pages for LINE and mobile-friendly web entry for Telegram.

**Tech Stack:** Flask, existing session-based auth (`app/utils/auth.py`), requests, APScheduler, dual DB support (Postgres + Mongo) via `user_repo`.

---

## Decisions Confirmed

- Web-first: Web app remains source of truth and best UX.
- LINE: Official Account + LIFF entrypoints, plus notifications.
- Telegram: Bot + interactive entrypoints (via web links), plus notifications.
- Binding: One-time binding code flow (multi-account supported).
- Add/Edit UX: Form-first (reuse existing `additem.html` / `edititem.html`), optimized for mobile entry.
- `PUBLIC_BASE_URL`: currently not set (plan supports running without it, but best UX requires it).

---

## Constraints / Notes

- Existing code has mixed auth (`flask_login` in `app/notifications/routes.py` vs session auth in `app/utils/auth.py`). For integrations UI we should consistently use session-based auth to avoid broken flows.
- Tests use `unittest` (not pytest). Use `python3 -m unittest ...`.

---

## Data Model (User)

We will store integration fields per user.

**Postgres (`app/models/user.py`)** add columns (strings are simplest for IDs):
- `line_notify_enabled: bool` (default False)
- `line_user_id: str` (default "")
- `tg_notify_enabled: bool` (default False)
- `tg_chat_id: str` (default "")
- `bind_code: str` (optional; store hashed or plain for v1)
- `bind_code_expires_at: str` (ISO string)
- `bind_code_channel: str` ("line"|"telegram")

**Mongo (`user` document)** store same keys.

If you prefer not to store bind code on User, we can add a separate collection/table later; for v1, user-scoped fields are simplest.

---

## Endpoints (New)

### Web UI
- `GET /notifications` (existing)
- `GET /notifications/` (existing settings page; we’ll extend UI)

### Integrations API (new blueprint)
- `POST /integrations/api/bind-code` (auth required)
  - body: `{ "channel": "line"|"telegram" }`
  - returns: `{ "code": "123456", "expires_at": "..." }`
- `POST /integrations/api/unbind` (auth required)
  - body: `{ "channel": "line"|"telegram" }`

### LINE
- `POST /integrations/line/webhook` (public)
  - verifies `X-Line-Signature` using `LINE_CHANNEL_SECRET`
  - supports: binding code messages, simple commands (e.g. “新增”, “修改”, “通知”) replying with LIFF/open-web links
- `POST /integrations/line/api/liff-login` (public)
  - body: `{ "access_token": "..." }`
  - backend calls LINE Profile API to get `userId`, maps to Web user, sets `session["UserID"]`
  - returns redirect url for desired action
- `GET /liff` (public)
  - lightweight LIFF page: shows “新增物品 / 修改物品 / 查看到期通知” cards, triggers `liff-login` then redirects.

### Telegram
- `POST /integrations/telegram/webhook/<secret>` (public)
  - handles `/start <code>` binding and simple commands
  - sends messages via Telegram Bot API

---

# Tasks

### Task 1: Add integration fields to user persistence

**Files:**
- Modify: `app/models/user.py`
- Modify: `app/repositories/user_repo.py`
- Test: `tests/test_user_service.py` (or new `tests/test_integrations.py`)

**Step 1: Write the failing test**

```python
# tests/test_integrations.py
import unittest
from unittest.mock import patch

from app.repositories import user_repo

class IntegrationsRepoTestCase(unittest.TestCase):
    def test_update_and_get_integration_settings(self):
        # Arrange
        username = "admin"

        # Act
        user_repo.update_integration_settings(
            username=username,
            line_notify_enabled=True,
            line_user_id="Uxxxxxxxx",
            tg_notify_enabled=True,
            tg_chat_id="123456789",
        )
        settings = user_repo.get_integration_settings(username)

        # Assert
        self.assertTrue(settings["line_notify_enabled"])
        self.assertEqual(settings["line_user_id"], "Uxxxxxxxx")
        self.assertTrue(settings["tg_notify_enabled"])
        self.assertEqual(settings["tg_chat_id"], "123456789")

if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run:
- `python3 -m unittest tests.test_integrations -v`

Expected: FAIL because `get_integration_settings` / `update_integration_settings` do not exist.

**Step 3: Write minimal implementation**

```python
# app/repositories/user_repo.py

def get_integration_settings(username: str) -> Dict[str, Any]:
    settings = get_notification_settings(username)
    # then add integration keys (defaults) from db record


def update_integration_settings(...):
    # postgres: update columns; mongo: $set fields
```

**Step 4: Run test to verify it passes**
- `python3 -m unittest tests.test_integrations -v`

**Step 5: Commit**
- `git add app/models/user.py app/repositories/user_repo.py tests/test_integrations.py`
- `git commit -m "feat: store LINE/TG integration settings"`

---

### Task 2: Implement binding-code generation + redemption

**Files:**
- Create: `app/services/integration_service.py`
- Modify: `app/services/__init__.py`
- Modify: `app/repositories/user_repo.py`
- Test: `tests/test_integrations.py`

**Step 1: Write failing test**

```python
class BindingCodeTestCase(unittest.TestCase):
    def test_generate_and_redeem_binding_code(self):
        username = "admin"
        code = integration_service.generate_binding_code(username, channel="line")
        self.assertTrue(code.isdigit())

        ok, bound_user = integration_service.redeem_binding_code(code, channel="line", external_id="U123")
        self.assertTrue(ok)
        self.assertEqual(bound_user, username)

        settings = user_repo.get_integration_settings(username)
        self.assertEqual(settings["line_user_id"], "U123")
```

**Step 2: Run red**
- `python3 -m unittest tests.test_integrations.BindingCodeTestCase -v`

**Step 3: Implement minimal**
- Use 6-digit code, TTL (e.g. 10 minutes)
- Store: code, expires_at, channel on user record
- Redeem: find user by code+channel (scan in mongo; query in postgres), verify expiry, set external id, clear code

**Step 4: Run green**

**Step 5: Commit**
- `git add app/services/integration_service.py app/repositories/user_repo.py tests/test_integrations.py`
- `git commit -m "feat: add one-time binding codes for LINE/TG"`

---

### Task 3: Add Integrations blueprint + settings API endpoints

**Files:**
- Create: `app/integrations/__init__.py`
- Create: `app/integrations/routes.py`
- Modify: `app/__init__.py` (register blueprint)
- Test: `tests/test_routes.py`

**Step 1: Write failing test**

```python
class IntegrationsRoutesTestCase(unittest.TestCase):
    def test_bind_code_requires_login(self):
        app = create_app()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        client = app.test_client()

        resp = client.post("/integrations/api/bind-code", json={"channel": "line"})
        self.assertEqual(resp.status_code, 302)
```

**Step 2: Run red**
- `python3 -m unittest tests.test_routes.RoutesTestCase -v`

**Step 3: Implement minimal**
- Use `from app.utils.auth import login_required, get_current_user`
- `POST /integrations/api/bind-code` calls `integration_service.generate_binding_code`

**Step 4: Run green**

**Step 5: Commit**

---

### Task 4: Implement LINE webhook (bind + commands)

**Files:**
- Create: `app/integrations/line.py`
- Modify: `app/integrations/routes.py` (mount LINE endpoints)
- Test: `tests/test_integrations_line.py`

**Step 1: Write failing test**

```python
import base64, hashlib, hmac, json

class LineWebhookTestCase(unittest.TestCase):
    def test_rejects_invalid_signature(self):
        app = create_app(); app.config["TESTING"] = True
        c = app.test_client()

        body = {"events": []}
        resp = c.post(
            "/integrations/line/webhook",
            data=json.dumps(body),
            headers={"Content-Type": "application/json", "X-Line-Signature": "bad"},
        )
        self.assertEqual(resp.status_code, 400)
```

**Step 2: Run red**
- `python3 -m unittest tests.test_integrations_line -v`

**Step 3: Implement minimal**
- Verify signature with `LINE_CHANNEL_SECRET`
- Parse events:
  - If text looks like binding code: redeem and reply “綁定成功”
  - If text == “新增”: reply with LIFF link (if `LINE_LIFF_ID` set) else web link

**Step 4: Run green**

**Step 5: Commit**

---

### Task 5: Implement Telegram webhook (bind + commands)

**Files:**
- Create: `app/integrations/telegram.py`
- Modify: `app/integrations/routes.py`
- Test: `tests/test_integrations_telegram.py`

**TDD steps:**
- Write failing test posting a Telegram update JSON, expect 200
- Implement parsing of `/start <code>` to bind chat_id
- Mock `requests.post` to avoid real API calls

---

### Task 6: Extend notification sending to LINE/TG

**Files:**
- Modify: `app/services/notification_service.py`
- Create: `app/services/chat_notify_service.py`
- Test: `tests/test_integrations.py`

**Behavior:**
- For each user who has expiry alerts:
  - Email: keep existing behavior
  - LINE: if `line_notify_enabled` and `line_user_id` set → push message
  - Telegram: if `tg_notify_enabled` and `tg_chat_id` set → send message

**TDD:** add test that patches sender functions and asserts correct calls.

---

### Task 7: Update Notifications Settings UI for LINE/TG

**Files:**
- Modify: `templates/notifications_settings.html`
- Modify: `app/notifications/routes.py` (if needed)

**UI/UX goals:**
- Show connection status (Connected/Not connected)
- Provide “產生綁定碼” button for LINE/TG
- Provide copy-to-clipboard and step-by-step instructions
- Provide toggles for LINE/TG notifications (separate from Email)

**Note:** If `app/notifications/routes.py` remains `flask_login`-based, convert it to session auth so it matches the rest of the app.

---

### Task 8: Add LIFF entry page and “open add/edit” routing

**Files:**
- Create: `templates/liff.html`
- Create: `app/liff/routes.py` (or add to integrations blueprint)

**Behavior:**
- LIFF shows 3 cards: Add / Edit / Notifications
- On click: call backend to establish session (using LINE access token → LINE profile API), then redirect to:
  - `/additem`
  - `/manageitem` (or a new “quick edit search” page later)
  - `/notifications`

**TDD:** unit-test the backend endpoint that maps LINE userId → username and sets session.

---

## Verification

Run (from repo/worktree root):
- `python3 -m unittest discover -s tests -v`

Optional:
- Run app locally and hit:
  - `/notifications/`
  - `/integrations/api/bind-code`
  - LINE/TG webhook endpoints via curl

---

## Rollout Checklist (Manual)

- Set env vars:
  - `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_LIFF_ID`
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`
  - `PUBLIC_BASE_URL` (strongly recommended)
- Configure LINE webhook URL to `https://<PUBLIC_BASE_URL>/integrations/line/webhook`
- Configure Telegram webhook URL to `https://<PUBLIC_BASE_URL>/integrations/telegram/webhook/<secret>`
- In Web app, generate binding code and bind accounts

