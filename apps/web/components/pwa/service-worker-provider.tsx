"use client"
import { useEffect } from "react"

export function ServiceWorkerProvider() {
  useEffect(() => {
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return
    if (process.env.NODE_ENV !== "production") return
    navigator.serviceWorker.register("/sw.js").catch(() => {})
  }, [])
  return null
}
