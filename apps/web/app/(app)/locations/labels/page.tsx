"use client"

import { useEffect, useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, Printer } from "lucide-react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Skeleton } from "@/components/ui/skeleton"
import { getBulkLocationLabelBundles } from "@/lib/api/location-labels"
import { listLocations } from "@/lib/api/locations"
import { useAccessToken } from "@/lib/auth/use-auth"

function idsFromQuery(queryString: string): number[] {
  const params = new URLSearchParams(queryString)
  return Array.from(
    new Set(
      params
        .getAll("ids")
        .map((value) => Number(value))
        .filter((value) => Number.isInteger(value) && value > 0),
    ),
  )
}

/**
 * 位置 QR 標籤列印頁（Phase 36）。
 *
 * - `?ids=1,2`：直接產生這些位置的標籤（由位置樹節點選單進入）
 * - 無 `ids`：列出全部位置供勾選（一次印多個櫃子／箱子）
 */
export default function LocationLabelsPage() {
  const t = useTranslations()
  const searchParams = useSearchParams()
  const token = useAccessToken()
  const urlIds = useMemo(
    () => idsFromQuery(searchParams.toString()),
    [searchParams],
  )
  const [picked, setPicked] = useState<number[]>([])

  const locations = useQuery({
    queryKey: ["locations", "labels"],
    queryFn: () => listLocations(token),
    enabled: token !== null && urlIds.length === 0,
    staleTime: 60_000,
  })

  // 有 ids → 用網址指定的；無 ids → 用勾選的
  const activeIds = urlIds.length > 0 ? urlIds : picked

  const labels = useQuery({
    queryKey: ["location-labels", activeIds],
    queryFn: () => getBulkLocationLabelBundles(activeIds, token),
    enabled: token !== null && activeIds.length > 0,
    staleTime: 60_000,
  })

  const [qrUrls, setQrUrls] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!labels.data) {
      setQrUrls({})
      return
    }
    const nextUrls: Record<string, string> = {}
    for (const bundle of labels.data.labels) {
      nextUrls[String(bundle.locationId)] = URL.createObjectURL(bundle.qrBlob)
    }
    setQrUrls(nextUrls)
    return () => {
      for (const url of Object.values(nextUrls)) URL.revokeObjectURL(url)
    }
  }, [labels.data])

  const toggle = (id: number, checked: boolean) => {
    setPicked((prev) =>
      checked ? [...prev, id] : prev.filter((value) => value !== id),
    )
  }

  const bundles = labels.data?.labels ?? []
  const skippedCount = labels.data?.skippedCount ?? 0
  const showPicker = urlIds.length === 0

  return (
    <section className="space-y-6 p-6 print:space-y-0 print:p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div>
          <h1 className="text-2xl font-semibold">{t("locations.labels.title")}</h1>
          <p className="text-sm text-muted-foreground">
            {showPicker
              ? t("locations.labels.pickerHint")
              : t("locations.labels.summary", { count: bundles.length })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/locations">
              <ArrowLeft className="h-4 w-4" />
              {t("locations.labels.backToLocations")}
            </Link>
          </Button>
          <Button
            type="button"
            onClick={() => window.print()}
            disabled={bundles.length === 0}
          >
            <Printer className="h-4 w-4" />
            {t("items.detail.print")}
          </Button>
        </div>
      </div>

      {showPicker ? (
        <div className="rounded-sm border p-3 print:hidden">
          <p className="mb-2 text-sm font-medium">{t("locations.labels.pickerTitle")}</p>
          {locations.isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : (locations.data?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">{t("locations.labels.empty")}</p>
          ) : (
            <ul className="space-y-1">
              {(locations.data ?? []).map((location) => (
                <li key={location.id} className="flex items-center gap-2">
                  <Checkbox
                    id={`location-label-${location.id}`}
                    checked={picked.includes(location.id)}
                    onCheckedChange={(checked) =>
                      toggle(location.id, checked === true)
                    }
                    aria-label={location.name}
                  />
                  <label
                    htmlFor={`location-label-${location.id}`}
                    className="text-sm"
                  >
                    {location.name}
                  </label>
                  <span className="text-xs text-muted-foreground">
                    {location.path === location.name ? "" : location.path}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      {skippedCount > 0 ? (
        <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm text-muted-foreground print:hidden">
          {t("locations.labels.skipped", { count: skippedCount })}
        </p>
      ) : null}

      {activeIds.length > 0 && bundles.length === 0 && !labels.isLoading ? (
        <p className="text-sm text-muted-foreground print:hidden">
          {t("locations.labels.notFound")}
        </p>
      ) : null}

      {bundles.length > 0 ? (
        <div className="grid justify-start gap-4 [grid-template-columns:repeat(auto-fill,minmax(6cm,6cm))] print:block">
          {bundles.map((bundle) => {
            const key = String(bundle.locationId)
            const qrUrl = qrUrls[key]
            return (
              <div
                key={key}
                data-testid={`location-label-${bundle.locationId}`}
                className="box-border flex min-h-[4cm] w-[6cm] break-inside-avoid flex-col items-center justify-center gap-1.5 rounded-sm border border-black/20 bg-white p-2 text-center text-black print:inline-flex print:rounded-none print:border print:border-black/20"
              >
                {qrUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={qrUrl}
                    alt={`QR code for ${bundle.label.name}`}
                    className="h-[2.65cm] w-[2.65cm]"
                  />
                ) : (
                  <div className="h-[2.65cm] w-[2.65cm] rounded-sm bg-neutral-100" />
                )}
                <div className="w-full truncate text-[0.75rem] font-semibold leading-tight">
                  {bundle.label.name}
                </div>
                <div className="w-full truncate text-[0.6rem] text-neutral-600">
                  {bundle.label.path}
                </div>
                <div className="w-full truncate text-[0.6rem] text-neutral-600">
                  {t("locations.labels.itemCount", {
                    count: bundle.label.item_count,
                  })}
                </div>
              </div>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}
