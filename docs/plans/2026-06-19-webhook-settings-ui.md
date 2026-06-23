# Webhook Settings UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the missing v2 webhook delivery/retry UI in Settings and tighten Settings page responsiveness.

**Architecture:** Keep backend behavior unchanged. Add a small typed webhooks API client, a focused `WebhookPanel` under Settings, and translations for Traditional Chinese and English. Use TanStack Query for list/delivery fetches and mutations, and keep the panel operational on mobile with scrollable tabs and stacked content.

**Tech Stack:** Next.js App Router, React, TanStack Query, shadcn/ui, Tailwind, next-intl, Vitest + Testing Library.

### Task 1: Webhook API Client

**Files:**

- Create: `apps/web/lib/api/webhooks.ts`
- Test: `apps/web/lib/api/webhooks.test.ts`

- [ ] Write failing tests for listing webhooks, listing deliveries with limit, retrying a delivery, and processing due retries.
- [ ] Run `pnpm --dir apps/web test -- lib/api/webhooks.test.ts` and confirm failure because the client does not exist.
- [ ] Implement the minimal API client using `apiFetch`.
- [ ] Re-run the client test and confirm it passes.

### Task 2: Webhook Settings Panel

**Files:**

- Create: `apps/web/components/settings/webhook-panel.tsx`
- Test: `apps/web/components/settings/webhook-panel.test.tsx`
- Modify: `apps/web/messages/zh-TW.json`
- Modify: `apps/web/messages/en.json`

- [ ] Write failing component tests that render webhook status, delivery history, retry action, process retries action, empty state, and loading state.
- [ ] Run `pnpm --dir apps/web test -- components/settings/webhook-panel.test.tsx` and confirm failure because the panel does not exist.
- [ ] Implement the panel with accessible labels, useful empty/loading/error states, and mobile-friendly delivery cards/table content.
- [ ] Re-run the component test and confirm it passes.

### Task 3: Settings Integration And Polish

**Files:**

- Modify: `apps/web/app/(app)/settings/page.tsx`
- Modify: `apps/web/messages/zh-TW.json`
- Modify: `apps/web/messages/en.json`

- [ ] Add a Webhooks tab between API Tokens and Import / Export.
- [ ] Make the tabs list horizontally scrollable on narrow screens and give tab content enough top spacing.
- [ ] Add concise page support copy so Settings feels organized rather than a bare tab strip.
- [ ] Run the targeted tests, then `pnpm --dir apps/web typecheck`.
- [ ] Verify in browser at desktop and mobile widths that Settings has no horizontal overflow and the new panel is usable.
