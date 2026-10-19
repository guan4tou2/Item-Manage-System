"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { useState } from "react"

import { AiSearchChips } from "@/components/items/ai-search-chips"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { SearchResponse } from "@/lib/api/ai-search"
import { getApiErrorDetail } from "@/lib/api/client"
import { useAiSearch } from "@/lib/hooks/use-ai-search"
import { filtersToSearchParams } from "@/lib/items/filters"
import type { ItemFilters } from "@/lib/api/items"

interface Props {
  /** 結果回報給列表頁（`null` 表示清除）。 */
  onResults: (result: SearchResponse | null) => void
}

/** 把 AI 解析出的條件轉成物品列表的 URL 參數（「在物品列表開啟」）。 */
function toItemFilters(result: SearchResponse): ItemFilters {
  const { applied } = result
  const filters: ItemFilters = {}
  if (applied.q) filters.q = applied.q
  if (applied.category) filters.categoryId = applied.category.id
  if (applied.location) filters.locationId = applied.location.id
  if (applied.tags.length > 0) filters.tagIds = applied.tags.map((tag) => tag.id)
  if (applied.expiry === "expired" || applied.expiry === "expiring_soon") {
    filters.expiry = applied.expiry
  }
  if (applied.sort === "expiry_asc" || applied.sort === "name_asc") {
    filters.sort = applied.sort
  }
  return filters
}

/**
 * AI 自然語言搜尋列（Phase 34）。
 *
 * - 送出 → 「理解中…」→ chip（可清除／在物品列表開啟）＋結果回報
 * - LLM 不可用：伺服器回 200＋`fallback_reason`，此處以中性提示說明（非錯誤）
 * - 未開啟資料分享：403 `ai_opt_in_required` → 引導至設定
 */
export function AiSearchBar({ onResults }: Props) {
  const t = useTranslations()
  const router = useRouter()
  const search = useAiSearch()
  const [query, setQuery] = useState("")
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [optInRequired, setOptInRequired] = useState(false)

  const submit = async () => {
    const text = query.trim()
    if (!text) return
    setOptInRequired(false)
    try {
      const response = await search.mutateAsync(text)
      setResult(response)
      onResults(response)
    } catch (error) {
      if (getApiErrorDetail(error) === "ai_opt_in_required") {
        setOptInRequired(true)
        setResult(null)
        onResults(null)
        return
      }
      setResult(null)
      onResults(null)
    }
  }

  const clear = () => {
    setResult(null)
    setOptInRequired(false)
    onResults(null)
  }

  const openInList = () => {
    if (!result) return
    const qs = filtersToSearchParams(toItemFilters(result)).toString()
    router.push(qs ? `/items?${qs}` : "/items")
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") void submit()
          }}
          placeholder={t("ai.search.placeholder")}
          aria-label={t("ai.search.aria")}
          className="min-w-0 flex-1"
        />
        <Button type="button" onClick={() => void submit()} disabled={search.isPending}>
          {search.isPending ? t("ai.search.thinking") : t("ai.search.submit")}
        </Button>
        {result !== null || optInRequired ? (
          <Button type="button" variant="ghost" onClick={clear}>
            {t("ai.search.clear")}
          </Button>
        ) : null}
      </div>

      {optInRequired ? (
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>{t("ai.search.optInRequired")}</span>
          <Link
            href="/settings/preferences"
            className="font-medium text-primary underline-offset-2 hover:underline"
          >
            {t("ai.search.openSettings")}
          </Link>
        </div>
      ) : null}

      {result !== null ? (
        <div className="space-y-2">
          {result.fallback_reason ? (
            <p role="status" className="text-xs text-muted-foreground">
              {t(`ai.search.fallback.${result.fallback_reason}`)}
            </p>
          ) : null}
          <AiSearchChips applied={result.applied} unresolved={result.unresolved} />
          {result.total === 0 ? (
            <p className="text-sm text-muted-foreground">{t("ai.search.noResults")}</p>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground">
                {t("items.list.page", { page: 1 })} · {result.total}
              </span>
              <Button type="button" size="sm" variant="outline" onClick={openInList}>
                {t("ai.search.openInList")}
              </Button>
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
