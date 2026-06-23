# IMS Workflow Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the next four workflow improvements: item bulk actions, template apply UX, stocktake efficiency, and low-stock notification/restock flows.

**Architecture:** Keep the current Next.js + FastAPI shape. Add API support only where the current backend cannot express the workflow, and keep frontend state local to the affected page or component. Every task should follow TDD: write a failing focused test, verify RED, implement the smallest passing change, then run targeted and full checks.

**Tech Stack:** Next.js 15, React Query, next-intl, shadcn/ui, FastAPI, SQLAlchemy async, pytest, Vitest, Playwright.

## Execution Order

1. **Item bulk actions**: highest daily-use impact and unlocks bulk label printing.
2. **Template apply UX**: small frontend-only UX pass after recent template work.
3. **Stocktake workflow**: improves warehouse/counting speed and review confidence.
4. **Low-stock notification/restock flow**: connects dashboard, notifications, item links, and shopping lists.

## Phase 1: Item Bulk Actions

### Task 1.1: Add backend bulk update and delete contracts

**Files:**
- Modify: `apps/api/app/schemas/item.py`
- Modify: `apps/api/app/routes/items.py`
- Modify: `apps/api/app/services/items_service.py`
- Test: `apps/api/tests/test_items_routes.py`
- Test: `apps/api/tests/test_items_service.py`
- Update generated types after API changes: `packages/api-types/openapi.json`, `packages/api-types/src/index.ts`

**TODO:**
- [ ] Add schemas for `ItemBulkUpdate`, `ItemBulkDelete`, and `ItemBulkResult`.
- [ ] Support bulk location/category updates and tag append/replace mode.
- [ ] Support soft-delete for multiple owned items.
- [ ] Reject cross-owner item IDs with 404/403 behavior consistent with single-item routes.
- [ ] Add route tests for successful update, successful delete, empty selection validation, and cross-owner protection.
- [ ] Add service tests for partial success avoidance: the operation should either apply to all visible owned IDs or fail.

**Commands:**
- RED/GREEN targeted API: `cd apps/api && uv run --extra test pytest -q tests/test_items_routes.py tests/test_items_service.py`
- Regenerate API types with the repo's existing OpenAPI/type generation command after implementation.

### Task 1.2: Add web bulk API client and tests

**Files:**
- Modify: `apps/web/lib/api/items.ts`
- Test: `apps/web/lib/api/items.test.ts` or create if absent

**TODO:**
- [ ] Add `bulkUpdateItems(body, token)`.
- [ ] Add `bulkDeleteItems(body, token)`.
- [ ] Test endpoint path, method, body serialization, and token pass-through.

**Commands:**
- `pnpm -F @ims/web test -- lib/api/items.test.ts`

### Task 1.3: Add selectable items table

**Files:**
- Modify: `apps/web/components/items/items-table.tsx`
- Create or modify: `apps/web/components/items/items-table.test.tsx`

**TODO:**
- [ ] Add row checkboxes and a header checkbox.
- [ ] Expose `selectedIds`, `onSelectionChange`, and `getRowDisabled` props.
- [ ] Keep row links and tags readable at mobile widths.
- [ ] Add tests for select one, select all visible rows, and clearing selection.

**Commands:**
- `pnpm -F @ims/web test -- components/items/items-table.test.tsx`

### Task 1.4: Add item list bulk action bar

**Files:**
- Modify: `apps/web/app/(app)/items/items-list-client.tsx`
- Create: `apps/web/app/(app)/items/items-list-client.test.tsx`
- Modify: `apps/web/messages/en.json`
- Modify: `apps/web/messages/zh-TW.json`

**TODO:**
- [ ] Show a sticky compact action bar when one or more items are selected.
- [ ] Show selected count.
- [ ] Add actions: add/replace tags, move location, delete.
- [ ] Invalidate `["items"]`, `["stats"]`, and relevant taxonomy queries after success.
- [ ] Confirm destructive delete before calling API.
- [ ] Ensure action bar wraps cleanly on 390px mobile width.

**Commands:**
- `pnpm -F @ims/web test -- 'app/(app)/items/items-list-client.test.tsx'`
- Browser check: `/items` at desktop and 390px, no horizontal overflow.

### Task 1.5: Add bulk label print page

**Files:**
- Create: `apps/web/app/(app)/items/labels/page.tsx`
- Modify: `apps/web/lib/api/labels.ts`
- Modify: `apps/web/app/(app)/items/items-list-client.tsx`
- Test: `apps/web/lib/api/labels.test.ts` or create if absent
- Test: `apps/web/app/(app)/items/labels/page.test.tsx`

**TODO:**
- [ ] Let the bulk action bar open `/items/labels?ids=<id>&ids=<id>`.
- [ ] Fetch label and QR data for selected IDs using the existing single-item label endpoints.
- [ ] Render a print-safe grid of 6x4cm labels.
- [ ] Add print button and back-to-items button.
- [ ] Handle missing/unauthorized labels with a skipped-count message.

**Commands:**
- `pnpm -F @ims/web test -- 'app/(app)/items/labels/page.test.tsx' lib/api/labels.test.ts`
- Browser print-layout check at desktop and 390px.

## Phase 2: Template Apply UX

### Task 2.1: Track applied template state in the item form

**Files:**
- Modify: `apps/web/components/items/item-form.tsx`
- Modify: `apps/web/components/items/item-form.test.tsx`
- Modify: `apps/web/messages/en.json`
- Modify: `apps/web/messages/zh-TW.json`

**TODO:**
- [ ] Store the currently applied template name/id in component state.
- [ ] After applying a template, show a compact status row: template name plus fields applied.
- [ ] Add a "Clear template values" action that resets only fields touched by the template, not user-entered unrelated values.
- [ ] Keep manually edited fields after apply marked dirty.
- [ ] Add tests for apply status, applied field summary, and clear action.

**Commands:**
- `pnpm -F @ims/web test -- components/items/item-form.test.tsx`

### Task 2.2: Improve template button UX

**Files:**
- Modify: `apps/web/components/items/item-form.tsx`
- Modify: `apps/web/components/items/item-form.test.tsx`

**TODO:**
- [ ] Highlight the active applied template.
- [ ] Disable clear when no template is active.
- [ ] Ensure long template names truncate without stretching the form.
- [ ] Verify keyboard focus remains in the form after apply/clear.

**Commands:**
- `pnpm -F @ims/web test -- components/items/item-form.test.tsx`

## Phase 3: Stocktake Workflow

### Task 3.1: Auto-focus next scan after recording

**Files:**
- Modify: `apps/web/components/stocktakes/stocktakes-client.tsx`
- Modify: `apps/web/components/stocktakes/stocktakes-client.test.tsx`
- Modify: `apps/web/messages/en.json`
- Modify: `apps/web/messages/zh-TW.json`

**TODO:**
- [ ] Add refs for item selector and quantity input.
- [ ] After a successful scan, clear quantity/note and focus the item selector for the next item.
- [ ] Add an accessible "Recorded, ready for next item" live message.
- [ ] Test focus behavior after scan success.

**Commands:**
- `pnpm -F @ims/web test -- components/stocktakes/stocktakes-client.test.tsx`

### Task 3.2: Group scanned rows by discrepancy status

**Files:**
- Modify: `apps/web/components/stocktakes/stocktakes-client.tsx`
- Modify: `apps/web/components/stocktakes/stocktakes-client.test.tsx`

**TODO:**
- [ ] Split rows into matched, missing, and over-counted groups based on delta.
- [ ] Show group counts near the scanned list heading.
- [ ] Keep existing per-row expected/actual/delta summaries.
- [ ] Add tests for group labels and row placement.

**Commands:**
- `pnpm -F @ims/web test -- components/stocktakes/stocktakes-client.test.tsx`

### Task 3.3: Confirm completion with discrepancy summary

**Files:**
- Modify: `apps/web/components/stocktakes/stocktakes-client.tsx`
- Modify: `apps/web/components/stocktakes/stocktakes-client.test.tsx`
- Use existing UI if available: `apps/web/components/ui/alert-dialog.tsx`

**TODO:**
- [ ] When completing a stocktake with discrepancies, show a confirmation dialog.
- [ ] Summarize matched/missing/over-counted counts and total delta.
- [ ] Keep immediate completion for zero-discrepancy sessions.
- [ ] Add tests for confirmation required vs not required.

**Commands:**
- `pnpm -F @ims/web test -- components/stocktakes/stocktakes-client.test.tsx`

## Phase 4: Low-Stock Notification and Restock Flow

### Task 4.1: Add "create restock list" from low-stock dashboard card

**Files:**
- Modify: `apps/web/components/dashboard/low-stock-card.tsx`
- Modify or create: `apps/web/components/dashboard/low-stock-card.test.tsx`
- Modify: `apps/web/lib/api/lists.ts`
- Modify: `apps/web/messages/en.json`
- Modify: `apps/web/messages/zh-TW.json`

**TODO:**
- [ ] Add a secondary action on low-stock card: create shopping list from low-stock items.
- [ ] Create a shopping list titled with the current date.
- [ ] Add list entries using item names and deficit quantities.
- [ ] Navigate to the created list after success.
- [ ] Add success/failure toast.
- [ ] Add tests for empty state hiding the CTA and populated state creating list entries.

**Commands:**
- `pnpm -F @ims/web test -- components/dashboard/low-stock-card.test.tsx`

### Task 4.2: Make notification opening wait for mark-read before navigation

**Files:**
- Modify: `apps/web/app/(app)/notifications/page.tsx`
- Modify: `apps/web/components/notifications/notification-item.tsx`
- Modify: `apps/web/components/notifications/notification-item.test.tsx`

**TODO:**
- [ ] Change open handler to `await markRead.mutateAsync(row.id)` before navigation when unread.
- [ ] Keep navigation immediate for already-read notifications.
- [ ] Add pending visual state for the opened notification row.
- [ ] Add tests that clicking unread notification marks read then navigates.

**Commands:**
- `pnpm -F @ims/web test -- components/notifications/notification-item.test.tsx`

### Task 4.3: Add direct restock CTA for low-stock notifications

**Files:**
- Modify: `apps/web/components/notifications/notification-item.tsx`
- Modify: `apps/web/app/(app)/notifications/page.tsx`
- Modify: `apps/web/messages/en.json`
- Modify: `apps/web/messages/zh-TW.json`

**TODO:**
- [ ] Detect `row.type === "low_stock"` and show a small "Add to restock list" action.
- [ ] Reuse the list creation helper from Task 4.1.
- [ ] Preserve the main row click behavior that opens the linked item.
- [ ] Add tests for CTA rendering only on low-stock notifications.

**Commands:**
- `pnpm -F @ims/web test -- components/notifications/notification-item.test.tsx`

## Final Verification

Run these before calling the whole backlog complete:

- `cd apps/api && uv run --extra test pytest -q`
- `pnpm -F @ims/web typecheck`
- `pnpm -F @ims/web test`
- `git diff --check`
- Browser QA with Playwright:
  - `/items`: bulk select, update, delete, label print at desktop and 390px.
  - `/items/new`: apply/clear template at desktop and 390px.
  - `/stocktakes`: scan, grouped discrepancies, completion confirmation.
  - `/dashboard` and `/notifications`: create restock list and open low-stock notification.
