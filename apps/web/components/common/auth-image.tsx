"use client"

import { useEffect, useState, type ComponentProps, type ReactNode } from "react"

import { useAccessToken } from "@/lib/auth/use-auth"
import { acquireBlobUrl, releaseBlobUrl } from "@/lib/images/blob-cache"

interface Props extends Omit<ComponentProps<"img">, "src"> {
  imageId: string
  /** 載入中顯示（預設退回 `fallback`）。 */
  placeholder?: ReactNode
  /** 取圖失敗／未登入時顯示（預設不渲染任何節點）。 */
  fallback?: ReactNode
}

/**
 * 需認證的圖片：`GET /api/images/{id}` 只接受 Bearer，`<img src>` 帶不了，
 * 因此以 blob cache 取回 blob 後轉 object URL 呈現。
 *
 * - 失敗（404／401／網路）與未登入一律顯示 `fallback`，不留下破圖
 * - 同一張圖跨元件實例共用 blob URL，減少重複下載
 * - 卸載或 `imageId` 變更時釋放引用，URL 由快取統一做 LRU 淘汰與 revoke
 */
export function AuthImage({ imageId, placeholder, fallback = null, alt, ...imgProps }: Props) {
  const token = useAccessToken()
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!token) {
      setFailed(true)
      return
    }
    let cancelled = false
    const activeImageId = imageId
    setUrl(null)
    setFailed(false)

    void (async () => {
      try {
        const objectUrl = await acquireBlobUrl(activeImageId, token)
        // 已取消時不在這裡 release：cleanup 已經釋放過這次 acquire，
        // 再放一次會多扣別的實例的引用（StrictMode 的雙重 effect 就會踩到）。
        if (!cancelled) setUrl(objectUrl)
      } catch {
        if (!cancelled) setFailed(true)
      }
    })()

    return () => {
      cancelled = true
      releaseBlobUrl(activeImageId)
    }
  }, [imageId, token])

  if (url !== null) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} {...imgProps} alt={alt ?? ""} onError={(event) => {
      setUrl(null)
      setFailed(true)
      imgProps.onError?.(event)
    }} />
  }
  if (failed) return <>{fallback}</>
  return <>{placeholder ?? fallback}</>
}
