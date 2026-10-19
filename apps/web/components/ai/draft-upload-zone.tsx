"use client"

import { useRef, useState } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { getApiErrorDetail } from "@/lib/api/client"
import { uploadImage } from "@/lib/api/images"
import { useAccessToken } from "@/lib/auth/use-auth"
import { useCreateDrafts } from "@/lib/hooks/use-ai-drafts"
import { useCreateReceipt } from "@/lib/hooks/use-ai-receipts"
import { cn } from "@/lib/utils"

/** 單次選取上限（＝API `image_ids` 上限；照片與收據頁共用）。 */
const MAX_FILES = 10
/** 伺服器端收據品項上限（與 `ai_service.MAX_RECEIPT_ITEMS` 一致）。 */
const MAX_RECEIPT_ITEMS = 50

type EntryStatus = "uploading" | "uploaded" | "failed"

interface Entry {
  key: string
  file: File
  status: EntryStatus
  imageId: string | null
}

/** 收據抽取失敗的代碼（伺服器以 `detail` 回代碼字串）。 */
const RECEIPT_ERROR_CODES = [
  "ai_disabled",
  "quota_exhausted",
  "upstream_error",
  "no_items",
] as const

type ReceiptErrorCode = (typeof RECEIPT_ERROR_CODES)[number]

function receiptErrorCode(error: unknown): ReceiptErrorCode | null {
  const detail = getApiErrorDetail(error)
  return RECEIPT_ERROR_CODES.find((code) => code === detail) ?? null
}

/**
 * 入庫上傳區（Phase 32 照片／Phase 33 收據）。
 *
 * 照片模式：逐檔上傳 → 一次建立草稿 → 清空選取（草稿入列後由佇列自動處理）
 * 收據模式：多頁上傳 → 一次抽取（每品項一列 `ready` 草稿）→ 清空選取
 *
 * - 單檔失敗留列可重試；建立／抽取失敗顯示區塊錯誤＋重試（保留已上傳的圖片）
 * - 孤立圖片與 item-form 既有行為一致（上傳後未建立草稿的檔案留在伺服器）
 */
export function DraftUploadZone() {
  const t = useTranslations()
  const token = useAccessToken()
  const create = useCreateDrafts()
  const createReceipt = useCreateReceipt()
  const inputRef = useRef<HTMLInputElement>(null)
  const nextKey = useRef(0)
  const [mode, setMode] = useState<"photo" | "receipt">("photo")
  const [entries, setEntries] = useState<Entry[]>([])
  const [ignored, setIgnored] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [createError, setCreateError] = useState(false)
  const [receiptError, setReceiptError] = useState<ReceiptErrorCode | null>(null)
  const [dragging, setDragging] = useState(false)

  const patch = (key: string, values: Partial<Entry>) => {
    setEntries((prev) => prev.map((entry) => (entry.key === key ? { ...entry, ...values } : entry)))
  }

  const reset = () => {
    setEntries([])
    setIgnored(0)
  }

  const createDrafts = async (imageIds: string[]) => {
    setCreateError(false)
    try {
      const result = await create.mutateAsync(imageIds)
      if (result.skipped_image_ids.length > 0) {
        toast.info(t("ai.drafts.upload.skipped", { count: result.skipped_image_ids.length }))
      }
      reset()
    } catch {
      setCreateError(true)
    }
  }

  const extractReceipt = async (imageIds: string[]) => {
    setReceiptError(null)
    try {
      const result = await createReceipt.mutateAsync(imageIds)
      if (result.truncated) {
        toast.info(t("ai.receipts.truncated", { count: MAX_RECEIPT_ITEMS }))
      }
      reset()
    } catch (error) {
      setReceiptError(receiptErrorCode(error))
    }
  }

  const submit = async (imageIds: string[]) => {
    if (imageIds.length === 0) return
    if (mode === "receipt") await extractReceipt(imageIds)
    else await createDrafts(imageIds)
  }

  const upload = async (targets: Entry[]) => {
    setUploading(true)
    setCreateError(false)
    setReceiptError(null)
    const imageIds: string[] = []
    for (const target of targets) {
      patch(target.key, { status: "uploading" })
      try {
        const meta = await uploadImage(target.file, token)
        imageIds.push(meta.id)
        patch(target.key, { status: "uploaded", imageId: meta.id })
      } catch {
        patch(target.key, { status: "failed" })
      }
    }
    setUploading(false)
    if (imageIds.length > 0) await submit(imageIds)
  }

  const accept = (files: File[]) => {
    const room = Math.max(MAX_FILES - entries.length, 0)
    const picked = files.slice(0, room)
    setIgnored(files.length - picked.length)
    if (picked.length === 0) return
    const added: Entry[] = picked.map((file) => ({
      key: `f${nextKey.current++}`,
      file,
      status: "uploading",
      imageId: null,
    }))
    setEntries((prev) => [...prev, ...added])
    void upload(added)
  }

  const onInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ""
    if (files.length > 0) accept(files)
  }

  const switchMode = (next: string) => {
    if (next === mode) return
    setMode(next === "receipt" ? "receipt" : "photo")
    reset()
    setCreateError(false)
    setReceiptError(null)
  }

  const uploadedIds = entries
    .filter((entry) => entry.status === "uploaded" && entry.imageId !== null)
    .map((entry) => entry.imageId as string)

  const isReceipt = mode === "receipt"
  const busy = uploading || create.isPending || createReceipt.isPending
  const errorMessage = isReceipt
    ? t(`ai.receipts.errors.${receiptError ?? "unknown"}`)
    : t("ai.drafts.upload.createFailed")

  return (
    <Card data-testid="draft-upload-zone">
      <CardHeader>
        <CardTitle className="text-base">
          {isReceipt ? t("ai.receipts.title") : t("ai.drafts.upload.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Tabs value={mode} onValueChange={switchMode}>
          <TabsList>
            <TabsTrigger value="photo">{t("ai.receipts.tabPhoto")}</TabsTrigger>
            <TabsTrigger value="receipt">{t("ai.receipts.tabReceipt")}</TabsTrigger>
          </TabsList>
        </Tabs>

        <div
          data-testid="draft-dropzone"
          className={cn(
            "rounded-md border border-dashed p-4 text-center",
            dragging && "border-primary bg-muted/40",
          )}
          onDragOver={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            accept(Array.from(event.dataTransfer?.files ?? []))
          }}
        >
          <p className="text-sm text-muted-foreground">
            {isReceipt ? t("ai.receipts.hint") : t("ai.drafts.upload.hint")}
          </p>
          <input
            ref={inputRef}
            id="draft-photos"
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            aria-label={isReceipt ? t("ai.receipts.aria") : t("ai.drafts.upload.aria")}
            onChange={onInputChange}
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="mt-3"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
          >
            {busy
              ? isReceipt
                ? t("ai.receipts.extracting")
                : t("ai.drafts.upload.creating")
              : isReceipt
                ? t("ai.receipts.choose")
                : t("ai.drafts.upload.choose")}
          </Button>
          {isReceipt && busy ? (
            <p className="mt-2 text-xs text-muted-foreground">
              {t("ai.receipts.extractingHint")}
            </p>
          ) : null}
        </div>

        {ignored > 0 ? (
          <p role="status" className="text-xs text-muted-foreground">
            {t("ai.drafts.upload.tooMany", { count: ignored })}
          </p>
        ) : null}

        {entries.length > 0 ? (
          <ul className="space-y-1">
            {entries.map((entry, index) => (
              <li
                key={entry.key}
                data-testid={`upload-file-${index}`}
                className="flex items-center justify-between gap-2 text-sm"
              >
                <span className="truncate">{entry.file.name}</span>
                <span className="flex items-center gap-2">
                  <span className="text-muted-foreground">
                    {entry.status === "uploading"
                      ? t("ai.drafts.upload.uploading")
                      : entry.status === "uploaded"
                        ? t("ai.drafts.upload.uploaded")
                        : t("ai.drafts.upload.uploadFailed")}
                  </span>
                  {entry.status === "failed" ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={uploading}
                      onClick={() => void upload([entry])}
                    >
                      {t("ai.drafts.upload.retry")}
                    </Button>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        ) : null}

        {(isReceipt ? receiptError !== null : createError) ? (
          <div className="flex flex-wrap items-center gap-2">
            <p role="alert" className="text-sm text-destructive">
              {errorMessage}
            </p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={busy || uploadedIds.length === 0}
              onClick={() => void submit(uploadedIds)}
            >
              {t("ai.drafts.upload.retry")}
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
