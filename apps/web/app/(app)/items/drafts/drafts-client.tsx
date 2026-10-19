"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { DraftBulkBar } from "@/components/ai/draft-bulk-bar"
import { DraftCard } from "@/components/ai/draft-card"
import { DraftUploadZone } from "@/components/ai/draft-upload-zone"
import { ViewerNotice } from "@/components/common/viewer-notice"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ApiError, getApiErrorDetail } from "@/lib/api/client"
import type { DraftAcceptRequest, DraftRead } from "@/lib/api/ai-drafts"
import type { CategoryTreeNode } from "@/lib/api/categories"
import type { LocationRead } from "@/lib/api/locations"
import { fallbackAcceptBody } from "@/lib/ai/draft-values"
import { useReadOnly } from "@/lib/auth/use-readonly"
import {
  useAcceptDraft,
  useDiscardDraft,
  useDiscardDrafts,
  useDrafts,
  useProcessDraft,
} from "@/lib/hooks/use-ai-drafts"
import { useCategories } from "@/lib/hooks/use-categories"
import { useLocations } from "@/lib/hooks/use-locations"
import { useTags } from "@/lib/hooks/use-tags"

/** 佇列一次載入的活動草稿上限。 */
const QUEUE_LIMIT = 50

/** `/items/drafts`：viewer 以提示卡取代整個佇列（不發出任何草稿查詢）。 */
export function DraftsClient() {
  const t = useTranslations()
  const readOnly = useReadOnly()

  if (readOnly) {
    return <ViewerNotice backHref="/items" backLabel={t("viewer.notice.backToList")} />
  }
  return <DraftsQueue />
}

/**
 * 草稿佇列：上傳區＋逐張處理迴圈＋批量條。
 *
 * - 處理迴圈序列化（同時最多 1 張，不引入背景 worker）；`pending` 自動續行、
 *   `processing` 不自動重送
 * - 業務性失敗（回應 200 但 `failed`）不中斷佇列；傳輸錯誤停止並提供「繼續處理」
 */
function DraftsQueue() {
  const t = useTranslations()
  const drafts = useDrafts({ limit: QUEUE_LIMIT })
  const categories = useCategories()
  const locations = useLocations()
  const tags = useTags()

  const process = useProcessDraft()
  const accept = useAcceptDraft()
  const discard = useDiscardDraft()
  const discardMany = useDiscardDrafts()

  const items = useMemo(() => drafts.data?.items ?? [], [drafts.data])
  const categoryTree: CategoryTreeNode[] = categories.data ?? []
  const locationNodes: LocationRead[] = locations.data ?? []
  const tagNames = useMemo(() => (tags.data ?? []).map((tag) => tag.name), [tags.data])

  const [processingId, setProcessingId] = useState<string | null>(null)
  const [pausedId, setPausedId] = useState<string | null>(null)
  const [acceptingId, setAcceptingId] = useState<string | null>(null)
  const [discardingId, setDiscardingId] = useState<string | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [bulk, setBulk] = useState<{ done: number; total: number } | null>(null)
  const [bulkDiscarding, setBulkDiscarding] = useState(false)

  // 本回合已送出處理的草稿（避免快取回寫前重複送出、重複消耗配額）
  const attemptedRef = useRef<Set<string>>(new Set())
  // 卡片回報的編輯值（批量接受時優先採用）
  const bodiesRef = useRef<Map<string, DraftAcceptRequest>>(new Map())
  const processRef = useRef(process.mutateAsync)
  processRef.current = process.mutateAsync

  const handleValuesChange = useCallback((id: string, body: DraftAcceptRequest) => {
    bodiesRef.current.set(id, body)
  }, [])

  // 逐張處理：序列、pending 自動續行
  useEffect(() => {
    if (pausedId !== null || processingId !== null) return
    const next = items.find(
      (draft) => draft.status === "pending" && !attemptedRef.current.has(draft.id),
    )
    if (!next) return

    setProcessingId(next.id)
    attemptedRef.current.add(next.id)
    void (async () => {
      try {
        await processRef.current(next.id)
      } catch (error) {
        // 終態衝突（409）／不存在（404）為業務性結果：略過續行
        if (!(error instanceof ApiError && (error.status === 409 || error.status === 404))) {
          setPausedId(next.id)
        }
      } finally {
        setProcessingId(null)
      }
    })()
  }, [items, processingId, pausedId])

  const isTransportError = (error: unknown) =>
    !(error instanceof ApiError && (error.status === 409 || error.status === 404))

  const handleProcess = async (id: string) => {
    if (processingId !== null) return
    setProcessingId(id)
    attemptedRef.current.add(id)
    try {
      await process.mutateAsync(id)
    } catch (error) {
      if (isTransportError(error)) {
        toast.error(getApiErrorDetail(error) ?? t("ai.drafts.queue.paused"))
      }
    } finally {
      setProcessingId(null)
    }
  }

  const resume = () => {
    if (pausedId === null) return
    // 允許重試中斷的那一張
    attemptedRef.current.delete(pausedId)
    setPausedId(null)
  }

  const handleAccept = async (id: string, body: DraftAcceptRequest) => {
    setAcceptingId(id)
    try {
      await accept.mutateAsync({ id, body })
      toast.success(t("ai.drafts.toast.accepted", { name: body.name }))
    } catch (error) {
      toast.error(getApiErrorDetail(error) ?? t("ai.drafts.toast.acceptFailed"))
    } finally {
      setAcceptingId(null)
    }
  }

  const handleDiscard = async (id: string) => {
    setDiscardingId(id)
    try {
      await discard.mutateAsync(id)
      toast.success(t("ai.drafts.toast.discarded"))
    } catch (error) {
      toast.error(getApiErrorDetail(error) ?? t("ai.drafts.toast.discardFailed"))
    } finally {
      setDiscardingId(null)
    }
  }

  const toggleSelection = (id: string, next: boolean) => {
    setSelected((prev) => {
      const copy = new Set(prev)
      if (next) copy.add(id)
      else copy.delete(id)
      return copy
    })
  }

  const acceptAll = async () => {
    const targets = items.filter((draft) => selected.has(draft.id))
    const ready = targets.filter((draft) => draft.status === "ready")
    const skipped = targets.length - ready.length
    if (ready.length === 0) {
      toast.info(t("ai.drafts.toast.bulkSkipped", { count: skipped }))
      return
    }

    setBulk({ done: 0, total: ready.length })
    let accepted = 0
    for (const [index, draft] of ready.entries()) {
      const body = bodiesRef.current.get(draft.id) ?? fallbackAcceptBody(draft, categoryTree)
      try {
        await accept.mutateAsync({ id: draft.id, body })
        accepted += 1
      } catch (error) {
        toast.error(getApiErrorDetail(error) ?? t("ai.drafts.toast.acceptFailed"))
      }
      setBulk({ done: index + 1, total: ready.length })
    }
    setBulk(null)
    setSelected(new Set())
    if (accepted > 0) toast.success(t("ai.drafts.toast.bulkAccepted", { count: accepted }))
    if (skipped > 0) toast.info(t("ai.drafts.toast.bulkSkipped", { count: skipped }))
  }

  const discardAll = async () => {
    const ids = Array.from(selected)
    if (ids.length === 0) return
    setBulkDiscarding(true)
    try {
      const result = await discardMany.mutateAsync(ids)
      toast.success(t("ai.drafts.toast.bulkDiscarded", { count: result.discarded }))
      if (result.skipped.length > 0) {
        toast.info(t("ai.drafts.toast.bulkSkipped", { count: result.skipped.length }))
      }
      setSelected(new Set())
    } catch (error) {
      toast.error(getApiErrorDetail(error) ?? t("ai.drafts.toast.discardFailed"))
    } finally {
      setBulkDiscarding(false)
    }
  }

  return (
    <div className="space-y-4">
      <DraftUploadZone />

      {drafts.isError ? (
        <div className="flex flex-wrap items-center gap-2">
          <p role="alert" className="text-sm text-destructive">
            {t("ai.drafts.queue.loadFailed")}
          </p>
          <Button size="sm" variant="outline" onClick={() => void drafts.refetch()}>
            {t("ai.drafts.queue.retry")}
          </Button>
        </div>
      ) : null}

      {pausedId !== null ? (
        <div className="flex flex-wrap items-center gap-2">
          <p role="alert" className="text-sm text-destructive">
            {t("ai.drafts.queue.paused")}
          </p>
          <Button size="sm" variant="outline" onClick={resume}>
            {t("ai.drafts.queue.resume")}
          </Button>
        </div>
      ) : null}

      {!drafts.isError && items.length > 0 ? (
        <DraftBulkBar
          selectedCount={items.filter((draft) => selected.has(draft.id)).length}
          totalCount={items.length}
          accepting={bulk}
          discarding={bulkDiscarding}
          onSelectAll={() => setSelected(new Set(items.map((draft) => draft.id)))}
          onClear={() => setSelected(new Set())}
          onAcceptAll={() => void acceptAll()}
          onDiscardAll={() => void discardAll()}
        />
      ) : null}

      {drafts.isLoading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((index) => (
            <Card key={index} data-testid="draft-card-skeleton">
              <CardContent className="flex gap-3 p-4">
                <Skeleton className="size-20 shrink-0" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-28" />
                  <Skeleton className="h-4 w-full" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : drafts.isError ? null : items.length === 0 ? (
        <Card data-testid="draft-empty">
          <CardContent className="p-6 text-center text-sm text-muted-foreground">
            <p className="font-medium text-foreground">{t("ai.drafts.empty.title")}</p>
            <p className="mt-1">{t("ai.drafts.empty.hint")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((draft: DraftRead) => (
            <DraftCard
              key={draft.id}
              draft={draft}
              categories={categoryTree}
              locations={locationNodes}
              tagSuggestions={tagNames}
              statusOverride={processingId === draft.id ? "processing" : undefined}
              selected={selected.has(draft.id)}
              onSelectedChange={(next) => toggleSelection(draft.id, next)}
              processing={processingId === draft.id}
              accepting={acceptingId === draft.id || bulk !== null}
              discarding={discardingId === draft.id || bulkDiscarding}
              onProcess={(id) => void handleProcess(id)}
              onAccept={(id, body) => void handleAccept(id, body)}
              onDiscard={(id) => void handleDiscard(id)}
              onValuesChange={handleValuesChange}
            />
          ))}
        </div>
      )}
    </div>
  )
}
