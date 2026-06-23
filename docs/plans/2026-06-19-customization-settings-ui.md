# Customization Settings UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a usable Settings entry for item types, custom fields, and item templates.

**Architecture:** Keep backend APIs unchanged. Add a typed web API client for customization endpoints, then add a focused Settings panel that lists, creates, and deletes item types, custom fields, and item templates. This is the first UI slice for customization; item form custom-value editing can follow after users can define fields.

**Tech Stack:** Next.js 15, React, TanStack Query, shadcn/ui, next-intl, Vitest, Testing Library.

### Task 1: Customization API Client

**Files:**
- Create: `apps/web/lib/api/customization.ts`
- Test: `apps/web/lib/api/customization.test.ts`

**Steps:**
1. Write failing tests for listing, creating, and deleting item types, custom fields, and item templates.
2. Run `pnpm -F @ims/web test -- lib/api/customization.test.ts` and verify the client is missing.
3. Implement the minimal API functions using `apiFetch`.
4. Re-run the targeted test and verify it passes.

### Task 2: Settings Panel

**Files:**
- Create: `apps/web/components/settings/customization-panel.tsx`
- Test: `apps/web/components/settings/customization-panel.test.tsx`
- Modify: `apps/web/app/(app)/settings/page.tsx`
- Modify: `apps/web/messages/en.json`
- Modify: `apps/web/messages/zh-TW.json`

**Steps:**
1. Write failing component tests for rendering existing records, creating a custom field, creating a template, and deleting an item type.
2. Run `pnpm -F @ims/web test -- components/settings/customization-panel.test.tsx` and verify the component is missing.
3. Implement the panel with three compact sections: item types, custom fields, templates.
4. Add a Settings tab and translations.
5. Re-run targeted tests.

### Task 3: Verification

**Files:**
- All files above.

**Steps:**
1. Run `pnpm -F @ims/web typecheck`.
2. Run `pnpm -F @ims/web test`.
3. Run `git diff --check`.
4. Report completed scope and remaining follow-up: custom values on item form/detail.
