"use client"

import { useEffect } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { applyUpdate, wireUpdateDetector } from "./sw-update-detector"

export function ServiceWorkerProvider() {
  const t = useTranslations()
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
            toast(t("pwa.update.ready"), {
              description: t("pwa.update.description"),
              duration: Infinity,
              action: {
                label: t("pwa.update.reload"),
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
