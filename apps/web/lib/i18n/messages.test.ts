import fs from "node:fs"
import path from "node:path"

import { describe, expect, it } from "vitest"

import en from "@/messages/en.json"
import zhTW from "@/messages/zh-TW.json"

type Messages = Record<string, unknown>

/** 攤平為 `a.b.c` 形式的葉節點路徑。 */
function keyPaths(node: Messages, prefix = ""): string[] {
  return Object.entries(node).flatMap(([key, value]) => {
    const path = prefix === "" ? key : `${prefix}.${key}`
    return value !== null && typeof value === "object"
      ? keyPaths(value as Messages, path)
      : [path]
  })
}

function leafValues(node: Messages, prefix = ""): Array<[string, unknown]> {
  return Object.entries(node).flatMap(([key, value]) => {
    const path = prefix === "" ? key : `${prefix}.${key}`
    return value !== null && typeof value === "object"
      ? leafValues(value as Messages, path)
      : ([[path, value]] as Array<[string, unknown]>)
  })
}

const enKeys = keyPaths(en as Messages).sort()
const zhKeys = keyPaths(zhTW as Messages).sort()

const messagesDir = path.resolve(__dirname, "..", "..", "messages")

/** Phase 32（AI 批次入庫）UI 表面的完整鍵清單。 */
const PHASE_32_KEYS = [
  // 共用 AI 記號
  "ai.mark.tooltip",
  // 佇列頁
  "ai.drafts.title",
  "ai.drafts.subtitle",
  "ai.drafts.backToNew",
  "ai.drafts.status.pending",
  "ai.drafts.status.processing",
  "ai.drafts.status.ready",
  "ai.drafts.status.failed",
  "ai.drafts.errors.ai_disabled",
  "ai.drafts.errors.quota_exhausted",
  "ai.drafts.errors.upstream_error",
  "ai.drafts.errors.image_missing",
  // 草稿卡
  "ai.drafts.card.photoAlt",
  "ai.drafts.card.untitled",
  "ai.drafts.card.select",
  "ai.drafts.card.retry",
  "ai.drafts.card.reprocess",
  "ai.drafts.card.manualToggle",
  "ai.drafts.card.historyBadge",
  "ai.drafts.card.suggest",
  "ai.drafts.card.suggesting",
  "ai.drafts.card.suggestEmpty",
  "ai.drafts.card.suggestFailed",
  "ai.drafts.card.accept",
  "ai.drafts.card.accepting",
  "ai.drafts.card.discard",
  "ai.drafts.card.discarding",
  // 上傳區
  "ai.drafts.upload.title",
  "ai.drafts.upload.hint",
  "ai.drafts.upload.choose",
  "ai.drafts.upload.aria",
  "ai.drafts.upload.uploading",
  "ai.drafts.upload.uploaded",
  "ai.drafts.upload.uploadFailed",
  "ai.drafts.upload.retry",
  "ai.drafts.upload.tooMany",
  "ai.drafts.upload.create",
  "ai.drafts.upload.creating",
  "ai.drafts.upload.createFailed",
  "ai.drafts.upload.skipped",
  // 佇列狀態
  "ai.drafts.queue.loadFailed",
  "ai.drafts.queue.retry",
  "ai.drafts.queue.paused",
  "ai.drafts.queue.resume",
  "ai.drafts.empty.title",
  "ai.drafts.empty.hint",
  // 批量條與提示
  "ai.drafts.bulk.selectAll",
  "ai.drafts.bulk.clear",
  "ai.drafts.bulk.selected",
  "ai.drafts.bulk.acceptAll",
  "ai.drafts.bulk.accepting",
  "ai.drafts.bulk.discardAll",
  "ai.drafts.bulk.discarding",
  "ai.drafts.toast.accepted",
  "ai.drafts.toast.acceptFailed",
  "ai.drafts.toast.discarded",
  "ai.drafts.toast.discardFailed",
  "ai.drafts.toast.bulkAccepted",
  "ai.drafts.toast.bulkDiscarded",
  "ai.drafts.toast.bulkSkipped",
  // 手動新增頁入口
  "items.new.batchEntry.title",
  "items.new.batchEntry.description",
  "items.new.batchEntry.cta",
  "items.new.batchEntry.badge",
  "items.new.batchEntry.badgeLoading",
  // 收據辨識（Phase 33）
  "ai.receipts.tabPhoto",
  "ai.receipts.tabReceipt",
  "ai.receipts.title",
  "ai.receipts.hint",
  "ai.receipts.choose",
  "ai.receipts.aria",
  "ai.receipts.extracting",
  "ai.receipts.extractingHint",
  "ai.receipts.errors.ai_disabled",
  "ai.receipts.errors.quota_exhausted",
  "ai.receipts.errors.upstream_error",
  "ai.receipts.errors.no_items",
  "ai.receipts.errors.unknown",
  "ai.receipts.truncated",
  "ai.receipts.group.unknownMerchant",
  "ai.receipts.group.unknownDate",
  "ai.receipts.group.pages",
  "ai.receipts.group.items",
  "ai.receipts.group.matched",
  "ai.receipts.group.mismatch",
  "ai.receipts.group.noTotal",
  "ai.receipts.item.subtotal",
  // AI 自然語言搜尋（Phase 34）
  "ai.search.toggle",
  "ai.search.placeholder",
  "ai.search.aria",
  "ai.search.submit",
  "ai.search.thinking",
  "ai.search.understood",
  "ai.search.clear",
  "ai.search.openInList",
  "ai.search.resultCount",
  "ai.search.noResults",
  "ai.search.unresolved",
  "ai.search.fallback.ai_disabled",
  "ai.search.fallback.quota_exhausted",
  "ai.search.fallback.upstream_error",
  "ai.search.fallback.unparsed",
  "ai.search.optInRequired",
  "ai.search.openSettings",
  "ai.search.labels.q",
  "ai.search.labels.category",
  "ai.search.labels.location",
  "ai.search.labels.tags",
  "ai.search.labels.expiry",
  "ai.search.labels.loan",
  "ai.search.labels.favorite",
  "ai.search.labels.quantity",
  "ai.search.labels.sort",
  "ai.search.expiry.expired",
  "ai.search.expiry.expiring_soon",
  "ai.search.loan.borrowed",
  "ai.search.loan.overdue",
  "ai.search.sort.expiry_asc",
  "ai.search.sort.name_asc",
  "ai.search.sort.created_desc",
  // 物品問答（Phase 34）
  "ai.ask.title",
  "ai.ask.description",
  "ai.ask.placeholder",
  "ai.ask.aria",
  "ai.ask.submit",
  "ai.ask.thinking",
  "ai.ask.disclaimer",
  "ai.ask.insufficient",
  "ai.ask.citations",
  "ai.ask.errors.ai_disabled",
  "ai.ask.errors.quota_exhausted",
  "ai.ask.errors.upstream_error",
  "ai.ask.errors.ai_opt_in_required",
  // 設定：AI 資料分享（Phase 34）
  "settings.preferences.aiSharing",
  "settings.preferences.aiSharingHint",
  "settings.preferences.aiSharingOn",
  "settings.preferences.aiSharingOff",
]

describe("i18n messages", () => {
  it("covers the Phase 36 location label surface in both locales", () => {
    const phase36Keys = [
      "locations.labels.title",
      "locations.labels.summary",
      "locations.labels.pickerTitle",
      "locations.labels.pickerHint",
      "locations.labels.empty",
      "locations.labels.backToLocations",
      "locations.labels.skipped",
      "locations.labels.notFound",
      "locations.labels.itemCount",
      "locations.tree.printLabel",
      "locations.tree.printLabels",
    ]
    const missingEn = phase36Keys.filter((key) => !enKeys.includes(key))
    const missingZh = phase36Keys.filter((key) => !zhKeys.includes(key))
    expect({ missingEn, missingZh }).toEqual({ missingEn: [], missingZh: [] })
  })

  it("has no unused keys in the Phase 36 location label namespaces", () => {
    const sources = [
      "app/(app)/locations/labels/page.tsx",
      "components/taxonomy/locations-panel.tsx",
      "components/taxonomy/location-tree-node.tsx",
    ]
      .map((relative) => fs.readFileSync(path.resolve(__dirname, "..", "..", relative), "utf8"))
      .join("\n")

    const keys = enKeys.filter(
      (key) =>
        key.startsWith("locations.labels.") ||
        key === "locations.tree.printLabel" ||
        key === "locations.tree.printLabels",
    )
    const missing = keys.filter((key) => !sources.includes(key))
    expect(missing).toEqual([])
  })
  it("keeps zh-TW and en in lockstep (same key set)", () => {
    expect(zhKeys).toEqual(enKeys)
  })

  it("keeps both locale files the same length", () => {
    const enLines = fs
      .readFileSync(path.join(messagesDir, "en.json"), "utf8")
      .split("\n")
    const zhLines = fs
      .readFileSync(path.join(messagesDir, "zh-TW.json"), "utf8")
      .split("\n")

    expect(zhLines.length).toBe(enLines.length)
  })

  it("covers the Phase 32 AI batch intake surface in both locales", () => {
    const missingEn = PHASE_32_KEYS.filter((key) => !enKeys.includes(key))
    const missingZh = PHASE_32_KEYS.filter((key) => !zhKeys.includes(key))

    expect({ en: missingEn, zhTW: missingZh }).toEqual({ en: [], zhTW: [] })
  })

  it("has no unused AI keys in the Phase 33 receipt namespace", () => {
    const sources = [
      "app/(app)/items/drafts/drafts-client.tsx",
      "components/ai/draft-upload-zone.tsx",
      "components/ai/receipt-group-header.tsx",
      "components/ai/draft-card.tsx",
    ]
      .map((relative) => fs.readFileSync(path.resolve(__dirname, "..", "..", relative), "utf8"))
      .join("\n")

    const receiptKeys = enKeys.filter((key) => key.startsWith("ai.receipts."))
    const missing = receiptKeys.filter((key) => {
      const suffix = key.slice("ai.receipts.".length)
      // 動態鍵（errors.*）以樣板字串組合，改用前綴檢查
      if (suffix.startsWith("errors.")) return !sources.includes("ai.receipts.errors.")
      return !sources.includes(key)
    })

    expect(missing).toEqual([])
  })

  it("has no unused keys in the Phase 34 AI search/ask namespaces", () => {
    const sources = [
      "components/items/ai-search-bar.tsx",
      "components/items/ai-search-chips.tsx",
      "components/items/ai-ask-panel.tsx",
      "components/settings/preferences-form.tsx",
      "app/(app)/items/items-list-client.tsx",
    ]
      .map((relative) => fs.readFileSync(path.resolve(__dirname, "..", "..", relative), "utf8"))
      .join("\n")

    const keys = enKeys.filter(
      (key) =>
        key.startsWith("ai.search.") ||
        key.startsWith("ai.ask.") ||
        key.startsWith("settings.preferences.aiSharing"),
    )
    // 動態鍵（`t(\`ai.search.fallback.${reason}\`)` 等）以命名空間前綴判定
    const dynamicNamespaces = [
      "ai.search.fallback.",
      "ai.search.labels.",
      "ai.search.expiry.",
      "ai.search.loan.",
      "ai.search.sort.",
      "ai.ask.errors.",
    ]
    const missing = keys.filter((key) => {
      const namespace = dynamicNamespaces.find((prefix) => key.startsWith(prefix))
      if (namespace) return !sources.includes(namespace)
      return !sources.includes(key)
    })

    expect(missing).toEqual([])
  })

  it("has no empty translations", () => {
    const emptyEn = leafValues(en as Messages)
      .filter(([, value]) => typeof value === "string" && value.trim() === "")
      .map(([key]) => key)
    const emptyZh = leafValues(zhTW as Messages)
      .filter(([, value]) => typeof value === "string" && value.trim() === "")
      .map(([key]) => key)

    expect({ en: emptyEn, zhTW: emptyZh }).toEqual({ en: [], zhTW: [] })
  })
})
