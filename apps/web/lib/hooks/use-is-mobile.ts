"use client"

import { useEffect, useState } from "react"

const QUERY = "(max-width: 767px)"

/**
 * 行動版判定（`< md`）。SSR 與 jsdom（無 matchMedia）一律回 `false`，
 * 由桌面分支渲染，避免測試與首次繪製閃動。
 */
export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return
    }
    const media = window.matchMedia(QUERY)
    setIsMobile(media.matches)
    const onChange = (event: MediaQueryListEvent) => setIsMobile(event.matches)
    media.addEventListener?.("change", onChange)
    return () => media.removeEventListener?.("change", onChange)
  }, [])

  return isMobile
}
