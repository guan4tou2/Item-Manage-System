"use client"

import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"

interface Props {
  selectedCount: number
  totalCount: number
  /** 批量接受進度（null＝未進行）。 */
  accepting: { done: number; total: number } | null
  discarding: boolean
  onSelectAll: () => void
  onClear: () => void
  onAcceptAll: () => void
  onDiscardAll: () => void
}

/** 佇列批量條：全選／取消、「全部接受」（僅 `ready`，其餘跳過）、「全部丟棄」。 */
export function DraftBulkBar({
  selectedCount,
  totalCount,
  accepting,
  discarding,
  onSelectAll,
  onClear,
  onAcceptAll,
  onDiscardAll,
}: Props) {
  const t = useTranslations()
  const busy = accepting !== null || discarding
  const nothingSelected = selectedCount === 0

  return (
    <div
      data-testid="draft-bulk-bar"
      className="flex flex-wrap items-center gap-2 rounded-md border bg-muted/40 px-3 py-2"
    >
      <Button
        type="button"
        size="sm"
        variant="ghost"
        disabled={busy || selectedCount === totalCount}
        onClick={onSelectAll}
      >
        {t("ai.drafts.bulk.selectAll")}
      </Button>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        disabled={busy || nothingSelected}
        onClick={onClear}
      >
        {t("ai.drafts.bulk.clear")}
      </Button>
      <span className="text-sm text-muted-foreground">
        {t("ai.drafts.bulk.selected", { count: selectedCount })}
      </span>
      <div className="ml-auto flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          disabled={busy || nothingSelected}
          onClick={onAcceptAll}
        >
          {accepting
            ? t("ai.drafts.bulk.accepting", { done: accepting.done, total: accepting.total })
            : t("ai.drafts.bulk.acceptAll")}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy || nothingSelected}
          onClick={onDiscardAll}
        >
          {discarding ? t("ai.drafts.bulk.discarding") : t("ai.drafts.bulk.discardAll")}
        </Button>
      </div>
    </div>
  )
}
