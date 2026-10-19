"use client"

import { Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { AiMark } from "@/components/ai/ai-mark"
import { AuthImage } from "@/components/common/auth-image"
import { CategorySelect } from "@/components/categories/category-select"
import { LocationSelect } from "@/components/locations/location-select"
import { TagMultiSelect } from "@/components/items/tag-multi-select"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { DraftAcceptRequest, DraftRead, DraftStatus } from "@/lib/api/ai-drafts"
import { getApiErrorDetail } from "@/lib/api/client"
import type { CategoryTreeNode } from "@/lib/api/categories"
import type { LocationRead } from "@/lib/api/locations"
import {
  acceptBodyFrom,
  seedDraftHistory,
  seedDraftValues,
  type DraftValues,
  type HistorySource,
} from "@/lib/ai/draft-values"
import { useSuggestClassification } from "@/lib/hooks/use-ai-drafts"

interface Props {
  draft: DraftRead
  categories: CategoryTreeNode[]
  locations: LocationRead[]
  tagSuggestions: string[]
  /** 佇列頁在送出處理請求期間的即時狀態（快取尚未回寫前顯示「辨識中」）。 */
  statusOverride?: DraftStatus
  selected?: boolean
  onSelectedChange?: (selected: boolean) => void
  processing?: boolean
  accepting?: boolean
  discarding?: boolean
  onProcess: (id: string) => void
  onAccept: (id: string, body: DraftAcceptRequest) => void
  onDiscard: (id: string) => void
  /** 回報目前編輯值（批量接受時由佇列頁取用）。 */
  onValuesChange?: (id: string, body: DraftAcceptRequest) => void
}

/**
 * 草稿卡（四態：排隊／辨識中／失敗／完成）。
 *
 * - 完成態：AI 欄位附 `AiMark`、歷史預設附「依歷史」徽章；可編輯後接受或丟棄
 * - 失敗態：錯誤碼文案＋重試辨識＋可展開的手動填寫（`failed → accepted` 為合法終態路徑）
 * - 接受中／丟棄中僅本卡按鈕 loading，其他卡不受影響
 */
export function DraftCard({
  draft,
  categories,
  locations,
  tagSuggestions,
  statusOverride,
  selected,
  onSelectedChange,
  processing = false,
  accepting = false,
  discarding = false,
  onProcess,
  onAccept,
  onDiscard,
  onValuesChange,
}: Props) {
  const t = useTranslations()
  const suggest = useSuggestClassification()

  const [values, setValues] = useState<DraftValues>(() => seedDraftValues(draft, categories))
  const [history, setHistory] = useState<HistorySource>(() => seedDraftHistory(draft))
  const [manualOpen, setManualOpen] = useState(false)
  const [suggesting, setSuggesting] = useState(false)
  const [suggestEmpty, setSuggestEmpty] = useState(false)
  const seededRef = useRef(`${draft.id}:${draft.status}`)
  const status = statusOverride ?? draft.status

  // 狀態推進（pending → ready、重試成功）時重新帶入建議；同一狀態重整不覆蓋使用者編輯
  const seedKey = `${draft.id}:${draft.status}`
  useEffect(() => {
    if (seededRef.current === seedKey) return
    seededRef.current = seedKey
    setValues(seedDraftValues(draft, categories))
    setHistory(seedDraftHistory(draft))
    setSuggestEmpty(false)
  }, [seedKey, draft, categories])

  // 回報目前編輯值給佇列頁（批量接受用）
  const reportRef = useRef(onValuesChange)
  reportRef.current = onValuesChange
  useEffect(() => {
    reportRef.current?.(draft.id, acceptBodyFrom(values))
  }, [draft.id, values])

  const ai = draft.payload.ai
  const displayName = ai?.name?.trim() || t("ai.drafts.card.untitled")
  const nameFilled = values.name.trim() !== ""

  const runSuggest = async () => {
    setSuggesting(true)
    try {
      const result = await suggest.mutateAsync(values.name.trim())
      setValues((prev) => ({
        ...prev,
        categoryId: result.category?.id ?? null,
        locationId: result.location?.id ?? null,
        tags: result.tags.map((tag) => tag.name),
      }))
      setHistory({
        category: result.category ? { id: result.category.id, name: result.category.name } : null,
        location: result.location
          ? { id: result.location.id, name: result.location.name }
          : null,
        tags: result.tags.map((tag) => tag.name),
      })
      setSuggestEmpty(
        !result.category && !result.location && result.tags.length === 0,
      )
    } catch (error: unknown) {
      toast.error(getApiErrorDetail(error) ?? t("ai.drafts.card.suggestFailed"))
    } finally {
      setSuggesting(false)
    }
  }

  const accept = () => {
    if (!nameFilled) return
    onAccept(draft.id, acceptBodyFrom(values))
  }

  const historyTagNames = history.tags.filter((tag) => values.tags.includes(tag))
  const showHistoryCategory =
    history.category !== null && values.categoryId === history.category.id
  const showHistoryLocation =
    history.location !== null && values.locationId === history.location.id

  const fields = (
    <div className="space-y-3">
      <div>
        <Label htmlFor={`draft-name-${draft.id}`}>{t("items.form.name")}</Label>
        <div className="flex items-center gap-2">
          <Input
            id={`draft-name-${draft.id}`}
            value={values.name}
            maxLength={200}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, name: event.target.value }))
            }
          />
          {ai ? <AiMark /> : null}
        </div>
      </div>

      <div>
        <Label htmlFor={`draft-description-${draft.id}`}>
          {t("items.form.description")}
        </Label>
        <div className="flex items-start gap-2">
          <Textarea
            id={`draft-description-${draft.id}`}
            rows={2}
            value={values.description}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, description: event.target.value }))
            }
          />
          {ai ? <AiMark /> : null}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <div className="flex min-h-6 items-center gap-2">
            <Label>{t("items.form.category")}</Label>
            {showHistoryCategory && history.category ? (
              <Badge
                variant="secondary"
                data-testid="draft-history-category-badge"
                className="font-normal"
              >
                {t("ai.drafts.card.historyBadge", { name: history.category.name })}
              </Badge>
            ) : null}
          </div>
          <CategorySelect
            value={values.categoryId}
            onChange={(id) => setValues((prev) => ({ ...prev, categoryId: id }))}
            categories={categories}
            label={t("items.form.category")}
            testId="draft-category-select"
          />
        </div>

        <div>
          <div className="flex min-h-6 items-center gap-2">
            <Label>{t("items.form.location")}</Label>
            {showHistoryLocation && history.location ? (
              <Badge
                variant="secondary"
                data-testid="draft-history-location-badge"
                className="font-normal"
              >
                {t("ai.drafts.card.historyBadge", { name: history.location.name })}
              </Badge>
            ) : null}
          </div>
          <LocationSelect
            value={values.locationId}
            onChange={(id) => setValues((prev) => ({ ...prev, locationId: id }))}
            nodes={locations}
            label={t("items.form.location")}
            testId="draft-location-select"
          />
        </div>
      </div>

      <div>
        <div className="flex min-h-6 items-center gap-2">
          <Label>{t("items.form.tags")}</Label>
          {historyTagNames.length > 0 ? (
            <Badge
              variant="secondary"
              data-testid="draft-history-tags-badge"
              className="font-normal"
            >
              {t("ai.drafts.card.historyBadge", { name: historyTagNames.join(", ") })}
            </Badge>
          ) : null}
        </div>
        <TagMultiSelect
          value={values.tags}
          onChange={(next) => setValues((prev) => ({ ...prev, tags: next }))}
          suggestions={tagSuggestions}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor={`draft-quantity-${draft.id}`}>{t("items.form.quantity")}</Label>
          <Input
            id={`draft-quantity-${draft.id}`}
            type="number"
            min={0}
            value={values.quantity}
            onChange={(event) =>
              setValues((prev) => ({
                ...prev,
                quantity: Number(event.target.value === "" ? 0 : event.target.value),
              }))
            }
          />
        </div>
        <div>
          <Label htmlFor={`draft-cost-${draft.id}`}>{t("items.form.cost")}</Label>
          <Input
            id={`draft-cost-${draft.id}`}
            inputMode="decimal"
            placeholder="0.00"
            value={values.cost}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, cost: event.target.value }))
            }
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={runSuggest}
          disabled={!nameFilled || suggesting || accepting || discarding}
        >
          {suggesting ? t("ai.drafts.card.suggesting") : t("ai.drafts.card.suggest")}
        </Button>
        {suggestEmpty ? (
          <p role="status" className="text-xs text-muted-foreground">
            {t("ai.drafts.card.suggestEmpty")}
          </p>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          onClick={accept}
          disabled={!nameFilled || accepting || discarding}
        >
          {accepting ? t("ai.drafts.card.accepting") : t("ai.drafts.card.accept")}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => onDiscard(draft.id)}
          disabled={accepting || discarding}
        >
          {discarding ? t("ai.drafts.card.discarding") : t("ai.drafts.card.discard")}
        </Button>
      </div>
    </div>
  )

  return (
    <Card data-testid={`draft-card-${draft.id}`} data-status={status}>
      <CardContent className="flex gap-3 p-4">
        {onSelectedChange ? (
          <Checkbox
            className="mt-1"
            checked={selected === true}
            aria-label={t("ai.drafts.card.select", { name: displayName })}
            onCheckedChange={(checked) => onSelectedChange(checked === true)}
          />
        ) : null}

        {draft.image_id ? (
          <AuthImage
            imageId={draft.image_id}
            alt={t("ai.drafts.card.photoAlt")}
            className="size-20 shrink-0 rounded-md border object-cover"
            fallback={
              <div className="flex size-20 shrink-0 items-center justify-center rounded-md border border-dashed text-xs text-muted-foreground">
                {t("ai.drafts.card.photoAlt")}
              </div>
            }
          />
        ) : (
          <div className="flex size-20 shrink-0 items-center justify-center rounded-md border border-dashed text-xs text-muted-foreground">
            {t("ai.drafts.card.photoAlt")}
          </div>
        )}

        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span
              data-testid="draft-status"
              aria-live="polite"
              className="text-sm font-medium text-muted-foreground"
            >
              {t(`ai.drafts.status.${status}`)}
            </span>
          </div>

          {status === "processing" ? (
            <div className="flex flex-wrap items-center gap-2">
              <Loader2 aria-hidden="true" className="size-4 animate-spin text-muted-foreground" />
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => onProcess(draft.id)}
                disabled={processing}
              >
                {t("ai.drafts.card.reprocess")}
              </Button>
            </div>
          ) : null}

          {status === "failed" ? (
            <div className="space-y-3">
              <p role="alert" className="text-sm text-destructive">
                {t(`ai.drafts.errors.${draft.error_code ?? "upstream_error"}`)}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => onProcess(draft.id)}
                  disabled={processing}
                >
                  {t("ai.drafts.card.retry")}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  aria-expanded={manualOpen}
                  onClick={() => setManualOpen((open) => !open)}
                >
                  {t("ai.drafts.card.manualToggle")}
                </Button>
              </div>
              {manualOpen ? fields : null}
            </div>
          ) : null}

          {status === "ready" ? fields : null}
        </div>
      </CardContent>
    </Card>
  )
}
