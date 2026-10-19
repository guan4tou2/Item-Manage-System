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
]

describe("i18n messages", () => {
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
