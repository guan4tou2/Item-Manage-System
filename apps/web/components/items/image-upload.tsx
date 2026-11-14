"use client"
import { useRef, useState } from "react"
import { useTranslations } from "next-intl"

import { AuthImage } from "@/components/common/auth-image"
import { Button } from "@/components/ui/button"
import { uploadImage } from "@/lib/api/images"
import { useAccessToken } from "@/lib/auth/use-auth"

interface Props {
  disabled?: boolean
  imageId: string | null
  onChange: (imageId: string | null) => void
}

export function ImageUpload({ imageId, onChange, disabled = false }: Props) {
  const t = useTranslations()
  const token = useAccessToken()
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)

  const onFile = async (file: File | undefined) => {
    if (!file || disabled) return
    setBusy(true)
    try {
      const meta = await uploadImage(file, token)
      onChange(meta.id)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2">
      {imageId ? (
        <AuthImage
          imageId={imageId}
          alt=""
          className="h-40 w-40 rounded-[0.25rem] border object-cover"
          placeholder={<div className="h-40 w-40 animate-pulse rounded-[0.25rem] border bg-muted" />}
        />
      ) : (
        <div className="flex h-40 w-40 items-center justify-center rounded-[0.25rem] border border-dashed text-xs text-muted-foreground">
          {t("items.form.noImage")}
        </div>
      )}
      <div className="flex gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy || disabled}
          onClick={() => inputRef.current?.click()}
        >
          {busy ? t("items.form.uploading") : t("items.form.uploadImage")}
        </Button>
        {imageId ? (
          <Button type="button" size="sm" variant="ghost" onClick={() => onChange(null)}>
            {t("items.form.removeImage")}
          </Button>
        ) : null}
      </div>
      <input
        ref={inputRef}
        type="file"
        disabled={disabled}
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={(e) => onFile(e.target.files?.[0])}
      />
    </div>
  )
}
