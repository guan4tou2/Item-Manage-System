"use client"

import { useRef, useState } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { uploadImage } from "@/lib/api/images"
import { useAccessToken } from "@/lib/auth/use-auth"
import { useCreateDrafts } from "@/lib/hooks/use-ai-drafts"
import { cn } from "@/lib/utils"

/** 單次選取上限（＝API `image_ids` 上限）。 */
const MAX_FILES = 10

type EntryStatus = "uploading" | "uploaded" | "failed"

interface Entry {
  key: string
  file: File
  status: EntryStatus
  imageId: string | null
}

/**
 * 批次上傳區：逐檔上傳 → 一次建立草稿 → 清空選取（草稿入列後由佇列自動處理）。
 *
 * - 單檔失敗留列可重試；建立失敗顯示區塊錯誤＋重試（保留已上傳的圖片）
 * - 孤立圖片與 item-form 既有行為一致（上傳後未建立草稿的檔案留在伺服器）
 */
export function DraftUploadZone() {
  const t = useTranslations()
  const token = useAccessToken()
  const create = useCreateDrafts()
  const inputRef = useRef<HTMLInputElement>(null)
  const nextKey = useRef(0)
  const [entries, setEntries] = useState<Entry[]>([])
  const [ignored, setIgnored] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [createError, setCreateError] = useState(false)
  const [dragging, setDragging] = useState(false)

  const patch = (key: string, values: Partial<Entry>) => {
    setEntries((prev) => prev.map((entry) => (entry.key === key ? { ...entry, ...values } : entry)))
  }

  const createDrafts = async (imageIds: string[]) => {
    setCreateError(false)
    try {
      const result = await create.mutateAsync(imageIds)
      if (result.skipped_image_ids.length > 0) {
        toast.info(t("ai.drafts.upload.skipped", { count: result.skipped_image_ids.length }))
      }
      setEntries([])
      setIgnored(0)
    } catch {
      setCreateError(true)
    }
  }

  const upload = async (targets: Entry[]) => {
    setUploading(true)
    setCreateError(false)
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
    if (imageIds.length > 0) await createDrafts(imageIds)
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

  const uploadedIds = entries
    .filter((entry) => entry.status === "uploaded" && entry.imageId !== null)
    .map((entry) => entry.imageId as string)

  return (
    <Card data-testid="draft-upload-zone">
      <CardHeader>
        <CardTitle className="text-base">{t("ai.drafts.upload.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
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
          <p className="text-sm text-muted-foreground">{t("ai.drafts.upload.hint")}</p>
          <input
            ref={inputRef}
            id="draft-photos"
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            aria-label={t("ai.drafts.upload.aria")}
            onChange={onInputChange}
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="mt-3"
            disabled={uploading || create.isPending}
            onClick={() => inputRef.current?.click()}
          >
            {uploading || create.isPending
              ? t("ai.drafts.upload.creating")
              : t("ai.drafts.upload.choose")}
          </Button>
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

        {createError ? (
          <div className="flex flex-wrap items-center gap-2">
            <p role="alert" className="text-sm text-destructive">
              {t("ai.drafts.upload.createFailed")}
            </p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={create.isPending || uploadedIds.length === 0}
              onClick={() => void createDrafts(uploadedIds)}
            >
              {t("ai.drafts.upload.retry")}
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
