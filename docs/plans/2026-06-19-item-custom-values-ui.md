# Item Custom Values UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let users fill and view custom field values on item create, edit, and detail screens.

**Status:** Completed on 2026-06-19.

**Verification:**
- `.venv/bin/python -m pytest tests/test_customization.py -q`
- `pnpm -F @ims/web test -- lib/api/customization.test.ts components/items/item-form.test.tsx components/items/item-custom-values-detail.test.tsx`
- `pnpm -F @ims/web typecheck`
- `pnpm -F @ims/web test`
- `git diff --check`
- Browser verified create/detail/edit custom values at 1280px and 390px with no horizontal overflow and no console warnings/errors.

**Architecture:** Keep custom field definitions managed in Settings. Add frontend API helpers for item custom values, render fields dynamically in `ItemForm`, persist values after item create/update, and show field/value pairs on item detail. Fix the API list response to unwrap stored JSON values so set/list return the same value shape.

**Tech Stack:** FastAPI, SQLAlchemy, Next.js 15, TanStack Query, next-intl, Vitest, pytest.

### Task 1: API Value Shape

**Files:**
- Modify: `apps/api/tests/test_customization.py`
- Modify: `apps/api/app/services/customization_service.py`

**Steps:**
1. Add a failing assertion that listed custom values return primitive values, not `{"v": value}`.
2. Run `.venv/bin/python -m pytest tests/test_customization.py -q` and verify failure.
3. Update `get_item_custom_values` to unwrap the stored value.
4. Re-run targeted pytest.

### Task 2: Web API Client

**Files:**
- Modify: `apps/web/lib/api/customization.test.ts`
- Modify: `apps/web/lib/api/customization.ts`

**Steps:**
1. Add failing tests for list/set/delete item custom values.
2. Run `pnpm -F @ims/web test -- lib/api/customization.test.ts`.
3. Implement the client helpers.
4. Re-run targeted test.

### Task 3: Item Form Dynamic Fields

**Files:**
- Modify: `apps/web/components/items/item-form.test.tsx`
- Modify: `apps/web/components/items/item-form.tsx`
- Modify: `apps/web/messages/en.json`
- Modify: `apps/web/messages/zh-TW.json`

**Steps:**
1. Add failing tests for schema custom values and dynamic custom field rendering.
2. Implement `custom_values`, `customFields`, and type-aware controls.
3. Re-run targeted form tests.

### Task 4: Create/Edit/Detail Integration

**Files:**
- Modify: `apps/web/app/(app)/items/new/page.tsx`
- Modify: `apps/web/app/(app)/items/[id]/edit/page.tsx`
- Modify: `apps/web/app/(app)/items/[id]/page.tsx`

**Steps:**
1. Fetch field definitions and existing values.
2. Persist custom values after create/update.
3. Display values on the detail page.
4. Run web typecheck/test and browser verification.
