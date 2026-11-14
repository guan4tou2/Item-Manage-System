"use client"

import { useEffect } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { applyUpdate, shouldReloadOnControllerChange, wireUpdateDetector } from "./sw-update-detector"

export function ServiceWorkerProvider() {
  const t = useTranslations()
  useEffect(() => {
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return
    if (process.env.NODE_ENV !== "production") return

    let cleanup: (() => void) | null = null
    let reloaded = false
    // 本頁載入起始時是否已受 SW 控制；首裝接管（null → worker）不重載。
    const initiallyControlled = Boolean(navigator.serviceWorker.controller)
    let updateAccepted = false

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
                onClick: () => {
                  updateAccepted = true
                  applyUpdate(waiting)
                },
              },
            })
          },
          onControllerChange: () => {
            if (!shouldReloadOnControllerChange({ reloaded, initiallyControlled, updateAccepted }))
              return
            reloaded = true
            window.location.reload()
          },
        })
      })
      .catch(() => {})

    return () => {
      cleanup?.()
    }
  // 僅於掛載時註冊；加入 t 會在語系切換時重新註冊並重設更新接受狀態。
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return null
}
