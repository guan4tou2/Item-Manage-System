"use client"
import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { imageUrl, uploadImage } from "@/lib/api/images"
import { useAccessToken } from "@/lib/auth/use-auth"

interface Props {
  imageId: string | null
  onChange: (imageId: string | null) => void
}

export function ImageUpload({ imageId, onChange }: Props) {
  const token = useAccessToken()
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)

  const onFile = async (file: File | undefined) => {
    if (!file) return
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
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={imageUrl(imageId)}
          alt=""
          className="h-40 w-40 rounded border object-cover"
        />
      ) : (
        <div className="flex h-40 w-40 items-center justify-center rounded border border-dashed text-xs text-muted-foreground">
          無圖片
        </div>
      )}
      <div className="flex gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
        >
          {busy ? "上傳中…" : "上傳圖片"}
        </Button>
        {imageId ? (
          <Button type="button" size="sm" variant="ghost" onClick={() => onChange(null)}>
            移除
          </Button>
        ) : null}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={(e) => onFile(e.target.files?.[0])}
      />
    </div>
  )
}
