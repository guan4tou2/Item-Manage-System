"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

type QrScannerModule = typeof import("qr-scanner").default

interface DecodedResult {
  payload: string
  at: number
}

/**
 * Best-effort extraction of an item UUID from a decoded QR payload.
 * Accepts either a full URL ending in /items/{uuid} or a bare UUID.
 * Returns null if we can't confidently identify one.
 */
export function extractItemIdFromPayload(payload: string): string | null {
  const trimmed = payload.trim()
  const uuidRe = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i

  // Try full URL → look for /items/<uuid> anywhere in the path
  try {
    const url = new URL(trimmed)
    const match = url.pathname.match(new RegExp(`/items/(${uuidRe.source})`))
    if (match && match[1]) return match[1].toLowerCase()
  } catch {
    // not a URL, fall through
  }

  // Bare-UUID fallback (whole payload is a UUID)
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(trimmed)) {
    return trimmed.toLowerCase()
  }
  return null
}

type Status = "idle" | "starting" | "scanning" | "denied" | "unsupported" | "error"

export function QrScannerView() {
  const t = useTranslations()
  const router = useRouter()
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const scannerRef = useRef<InstanceType<QrScannerModule> | null>(null)
  const [status, setStatus] = useState<Status>("idle")
  const [lastResult, setLastResult] = useState<DecodedResult | null>(null)
  const [manualValue, setManualValue] = useState("")

  const handleDecoded = useCallback(
    (payload: string) => {
      setLastResult({ payload, at: Date.now() })
      const id = extractItemIdFromPayload(payload)
      if (id) {
        // Stop scanning immediately so we don't double-navigate
        scannerRef.current?.stop()
        setStatus("idle")
        router.push(`/items/${id}` as never)
      }
    },
    [router],
  )

  const start = useCallback(async () => {
    if (!videoRef.current) return
    setStatus("starting")
    try {
      // Dynamic import so we never ship the WASM blob to first paint
      const mod = await import("qr-scanner")
      const QrScanner = mod.default
      const hasCam = await QrScanner.hasCamera()
      if (!hasCam) {
        setStatus("unsupported")
        return
      }
      const scanner = new QrScanner(
        videoRef.current,
        (result) => handleDecoded(result.data),
        {
          highlightScanRegion: true,
          highlightCodeOutline: true,
          preferredCamera: "environment",
        },
      )
      scannerRef.current = scanner
      await scanner.start()
      setStatus("scanning")
    } catch (err: unknown) {
      const msg = (err as Error)?.message ?? ""
      if (/permission|denied|notallowed/i.test(msg)) {
        setStatus("denied")
      } else {
        setStatus("error")
      }
    }
  }, [handleDecoded])

  useEffect(() => {
    // Auto-start on mount
    void start()
    return () => {
      scannerRef.current?.stop()
      scannerRef.current?.destroy()
      scannerRef.current = null
    }
  }, [start])

  function handleManualSubmit(e: React.FormEvent) {
    e.preventDefault()
    const id = extractItemIdFromPayload(manualValue)
    if (id) {
      router.push(`/items/${id}` as never)
      return
    }
    // not a URL or bare UUID — treat as plain name search
    if (manualValue.trim()) {
      router.push(`/items?q=${encodeURIComponent(manualValue.trim())}` as never)
    }
  }

  return (
    <div className="space-y-4">
      <div className="relative mx-auto aspect-square w-full max-w-md overflow-hidden rounded border bg-black">
        <video
          ref={videoRef}
          className="h-full w-full object-cover"
          playsInline
          muted
        />
        {status !== "scanning" ? (
          <div className="absolute inset-0 flex items-center justify-center bg-black/60 p-4 text-center text-sm text-white">
            {status === "starting" && t("scan.camera.starting")}
            {status === "idle" && t("scan.camera.idle")}
            {status === "denied" && t("scan.camera.denied")}
            {status === "unsupported" && t("scan.camera.unsupported")}
            {status === "error" && t("scan.camera.error")}
          </div>
        ) : null}
      </div>

      {lastResult ? (
        <div className="rounded border bg-muted/30 p-3 text-xs">
          <div className="text-muted-foreground">{t("scan.result.label")}</div>
          <code className="block break-all font-mono">{lastResult.payload}</code>
          {extractItemIdFromPayload(lastResult.payload) ? (
            <div className="mt-1 text-green-700">{t("scan.result.found")}</div>
          ) : (
            <div className="mt-1 text-muted-foreground">
              {t("scan.result.notFound")}
            </div>
          )}
        </div>
      ) : null}

      <form onSubmit={handleManualSubmit} className="space-y-2">
        <Label className="block">
          {t("scan.manual.label")}
        </Label>
        <div className="flex gap-2">
          <Input
            type="text"
            value={manualValue}
            onChange={(e) => setManualValue(e.target.value)}
            placeholder={t("scan.manual.placeholder")}
            className="flex-1"
          />
          <Button type="submit">{t("scan.manual.go")}</Button>
        </div>
      </form>

      {status !== "scanning" ? (
        <Button variant="outline" onClick={() => void start()} disabled={status === "starting"}>
          {status === "starting" ? t("scan.camera.starting") : t("scan.camera.restart")}
        </Button>
      ) : null}
    </div>
  )
}
