"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useBarcodeLookup } from "@/lib/hooks/use-barcode-lookup"
import { canonicalizeBarcode, isBarcodeLike } from "@/lib/scan/barcode"
import { createBarcodeEngine, type BarcodeEngine } from "@/lib/scan/barcode-engine"
import {
  extractLocationIdFromPayload,
  locationItemsPath,
} from "@/lib/scan/location-link"

import { BarcodeCandidates } from "./barcode-candidates"
import { BarcodeExternalCard } from "./barcode-external-card"

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
  const engineRef = useRef<BarcodeEngine | null>(null)
  const [status, setStatus] = useState<Status>("idle")
  const [lastResult, setLastResult] = useState<DecodedResult | null>(null)
  const [manualValue, setManualValue] = useState("")
  const [lookupCode, setLookupCode] = useState<string | null>(null)
  const lookup = useBarcodeLookup(lookupCode)

  const stopEngine = useCallback(() => {
    engineRef.current?.stop()
    engineRef.current = null
  }, [])

  /** 條碼候選 → 內查／外查流程（掃描與手動輸入共用）。 */
  const startLookup = useCallback(
    (raw: string) => {
      stopEngine()
      setStatus("idle")
      setLookupCode(canonicalizeBarcode(raw))
    },
    [stopEngine],
  )

  const handleDecoded = useCallback(
    (payload: string) => {
      setLastResult({ payload, at: Date.now() })
      const id = extractItemIdFromPayload(payload)
      if (id) {
        // Stop scanning immediately so we don't double-navigate
        stopEngine()
        setStatus("idle")
        router.push(`/items/${id}` as never)
        return
      }
      // Phase 36：位置標籤（/items?location={id}）→ 該位置的物品清單
      const locationId = extractLocationIdFromPayload(payload)
      if (locationId) {
        stopEngine()
        setStatus("idle")
        router.push(locationItemsPath(locationId) as never)
        return
      }
      if (isBarcodeLike(payload)) {
        startLookup(payload)
      }
    },
    [router, startLookup, stopEngine],
  )

  // 內查單筆命中 → 直接跳物品頁（§5.4）
  useEffect(() => {
    const matches = lookup.data?.local_matches
    if (matches?.length === 1 && matches[0]) {
      router.push(`/items/${matches[0].id}` as never)
    }
  }, [lookup.data, router])

  const start = useCallback(async () => {
    const video = videoRef.current
    if (!video) return
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("unsupported")
      return
    }
    stopEngine()
    setStatus("starting")
    try {
      engineRef.current = await createBarcodeEngine(video, handleDecoded)
      setStatus("scanning")
    } catch (err: unknown) {
      const name = (err as Error)?.name ?? ""
      const msg = (err as Error)?.message ?? ""
      if (name === "NotAllowedError" || /permission|denied|notallowed/i.test(msg)) {
        setStatus("denied")
      } else if (name === "NotFoundError" || name === "NotReadableError") {
        setStatus("unsupported")
      } else {
        setStatus("error")
      }
    }
  }, [handleDecoded, stopEngine])

  useEffect(() => {
    // Auto-start on mount
    void start()
    return () => {
      stopEngine()
    }
  }, [start, stopEngine])

  function handleManualSubmit(e: React.FormEvent) {
    e.preventDefault()
    const value = manualValue.trim()
    if (!value) return
    const id = extractItemIdFromPayload(value)
    if (id) {
      router.push(`/items/${id}` as never)
      return
    }
    // Phase 36：位置深連結 → 該位置的物品清單
    const locationId = extractLocationIdFromPayload(value)
    if (locationId) {
      router.push(locationItemsPath(locationId) as never)
      return
    }
    if (isBarcodeLike(value)) {
      startLookup(value)
      return
    }
    // not a URL, UUID, or barcode — treat as plain name search
    router.push(`/items?q=${encodeURIComponent(value)}` as never)
  }

  const matches = lookup.data?.local_matches ?? []

  return (
    <div className="space-y-4">
      <div className="relative mx-auto aspect-square w-full max-w-md overflow-hidden rounded-[0.25rem] border bg-black">
        <video
          ref={videoRef}
          className="h-full w-full object-cover"
          playsInline
          muted
        />
        {status === "scanning" ? (
          <div
            className="pointer-events-none absolute inset-8 rounded-[0.25rem] border-2 border-white/70"
            aria-hidden
          />
        ) : null}
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

      {lookupCode && lookup.isFetching ? (
        <div data-testid="barcode-lookup-loading" className="rounded-[0.25rem] border p-3 text-sm">
          {t("scan.lookup.loading")}
        </div>
      ) : null}

      {lookupCode && lookup.isError && !lookup.isFetching ? (
        <div data-testid="barcode-lookup-error" className="space-y-3 rounded-[0.25rem] border p-3">
          <p className="text-sm">{t("scan.lookup.error")}</p>
          <Button onClick={() => void lookup.refetch()}>{t("scan.lookup.retry")}</Button>
        </div>
      ) : null}

      {matches.length > 1 ? <BarcodeCandidates matches={matches} /> : null}

      {lookupCode && lookup.data && matches.length === 0 ? (
        <BarcodeExternalCard
          result={lookup.data}
          onRetry={() => void lookup.refetch()}
        />
      ) : null}

      {lastResult ? (
        <div className="rounded-[0.25rem] border bg-muted/30 p-3 text-xs">
          <div className="text-muted-foreground">{t("scan.result.label")}</div>
          <code className="block break-all font-mono">{lastResult.payload}</code>
          {extractItemIdFromPayload(lastResult.payload) ? (
            <div className="mt-1 text-green-700">{t("scan.result.found")}</div>
          ) : isBarcodeLike(lastResult.payload) ? (
            <div className="mt-1 text-green-700">
              {t("scan.result.barcode", {
                code: canonicalizeBarcode(lastResult.payload),
              })}
            </div>
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
          {status === "starting"
            ? t("scan.camera.starting")
            : status === "denied"
              ? t("scan.camera.grantPermission")
              : t("scan.camera.restart")}
        </Button>
      ) : null}
    </div>
  )
}
