"use client"

import { useEffect } from "react"
import { toast } from "sonner"

import { applyUpdate, wireUpdateDetector } from "./sw-update-detector"

export function ServiceWorkerProvider() {
  useEffect(() => {
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return
    if (process.env.NODE_ENV !== "production") return

    let cleanup: (() => void) | null = null
    let reloaded = false

    navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => {
        cleanup = wireUpdateDetector(registration, navigator.serviceWorker, {
          onUpdateReady: (waiting) => {
            toast("新版已準備好", {
              description: "重新載入以套用更新",
              duration: Infinity,
              action: {
                label: "重新載入",
                onClick: () => applyUpdate(waiting),
              },
            })
          },
          onControllerChange: () => {
            if (reloaded) return
            reloaded = true
            window.location.reload()
          },
        })
      })
      .catch(() => {})

    return () => {
      cleanup?.()
    }
  }, [])

  return null
}
