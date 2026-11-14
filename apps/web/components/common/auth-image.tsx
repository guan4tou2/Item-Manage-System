"use client"

import { useEffect, useState, type ComponentProps, type ReactNode } from "react"

import { apiFetch } from "@/lib/api/client"
import { useAccessToken } from "@/lib/auth/use-auth"

interface Props extends Omit<ComponentProps<"img">, "src"> {
  imageId: string
  /** 載入中顯示（預設退回 `fallback`）。 */
  placeholder?: ReactNode
  /** 取圖失敗／未登入時顯示（預設不渲染任何節點）。 */
  fallback?: ReactNode
}

/**
 * 需認證的圖片：`GET /api/images/{id}` 只接受 Bearer，`<img src>` 帶不了，
 * 因此以 `apiFetch` 取回 blob 後轉 object URL 呈現。
 *
 * - 失敗（404／401／網路）與未登入一律顯示 `fallback`，不留下破圖
 * - 卸載或 `imageId` 變更時撤銷 object URL
 */
export function AuthImage({ imageId, placeholder, fallback = null, ...imgProps }: Props) {
  const token = useAccessToken()
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!token) {
      setFailed(true)
      return
    }
    let cancelled = false
    let objectUrl: string | null = null
    setUrl(null)
    setFailed(false)

    void (async () => {
      try {
        const response = await apiFetch(`/images/${imageId}`, { accessToken: token })
        const blob = await response.blob()
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      } catch {
        if (!cancelled) setFailed(true)
      }
    })()

    return () => {
      cancelled = true
      if (objectUrl !== null) URL.revokeObjectURL(objectUrl)
    }
  }, [imageId, token])

  if (url !== null) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} {...imgProps} onError={(event) => {
      setUrl(null)
      setFailed(true)
      imgProps.onError?.(event)
    }} />
  }
  if (failed) return <>{fallback}</>
  return <>{placeholder ?? fallback}</>
}
