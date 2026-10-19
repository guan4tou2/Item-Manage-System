"use client"

import { useTranslations } from "next-intl"

import { AiMark } from "@/components/ai/ai-mark"
import { Badge } from "@/components/ui/badge"
import type { AppliedFilters } from "@/lib/api/ai-search"

interface Props {
  applied: AppliedFilters
  unresolved: string[]
}

/** 「理解為」chip 群：把 AI 解析出的條件顯示為可讀標籤（含未解析名稱）。 */
export function AiSearchChips({ applied, unresolved }: Props) {
  const t = useTranslations()
  const labels: string[] = []

  if (applied.q) labels.push(t("ai.search.labels.q", { value: applied.q }))
  if (applied.category) {
    labels.push(t("ai.search.labels.category", { value: applied.category.name }))
  }
  if (applied.location) {
    labels.push(
      t("ai.search.labels.location", {
        value: applied.location.path ?? applied.location.name,
      }),
    )
  }
  if (applied.tags.length > 0) {
    labels.push(
      t("ai.search.labels.tags", {
        value: applied.tags.map((tag) => tag.name).join(", "),
      }),
    )
  }
  if (applied.expiry) {
    labels.push(
      t("ai.search.labels.expiry", { value: t(`ai.search.expiry.${applied.expiry}`) }),
    )
  }
  if (applied.loan) {
    labels.push(t("ai.search.labels.loan", { value: t(`ai.search.loan.${applied.loan}`) }))
  }
  if (applied.favorite === true) labels.push(t("ai.search.labels.favorite"))
  if (applied.min_quantity !== null || applied.max_quantity !== null) {
    const range =
      applied.min_quantity !== null && applied.max_quantity !== null
        ? `${applied.min_quantity}–${applied.max_quantity}`
        : applied.min_quantity !== null
          ? `≥${applied.min_quantity}`
          : `≤${applied.max_quantity}`
    labels.push(t("ai.search.labels.quantity", { value: range }))
  }
  if (applied.sort) {
    labels.push(
      t("ai.search.labels.sort", { value: t(`ai.search.sort.${applied.sort}`) }),
    )
  }

  if (labels.length === 0 && unresolved.length === 0) return null

  return (
    <div
      data-testid="ai-search-chips"
      className="flex flex-wrap items-center gap-2"
      aria-live="polite"
    >
      <span className="flex items-center gap-1 text-xs text-muted-foreground">
        <AiMark />
        {t("ai.search.understood")}
      </span>
      {labels.map((label) => (
        <Badge key={label} variant="secondary" className="font-normal">
          {label}
        </Badge>
      ))}
      {unresolved.map((entry) => {
        const [, name = entry] = entry.split(":", 2)
        return (
          <Badge
            key={entry}
            variant="outline"
            className="border-dashed font-normal text-muted-foreground"
            title={entry}
          >
            {t("ai.search.unresolved", { name })}
          </Badge>
        )
      })}
    </div>
  )
}
