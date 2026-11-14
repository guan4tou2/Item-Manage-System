"use client"

import { useEffect, useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, FileDown, Printer } from "lucide-react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { LabelBarcode } from "@/components/items/label-barcode"
import { getBulkItemLabelBundles, getItemLabelsPdf } from "@/lib/api/labels"
import { useAccessToken } from "@/lib/auth/use-auth"

function uniqueIdsFromQuery(queryString: string): string[] {
  const params = new URLSearchParams(queryString)
  return Array.from(new Set(params.getAll("ids").filter(Boolean)))
}

export default function BulkItemLabelsPage() {
  const t = useTranslations()
  const searchParams = useSearchParams()
  const token = useAccessToken()
  const ids = useMemo(
    () => uniqueIdsFromQuery(searchParams.toString()),
    [searchParams],
  )
  const labels = useQuery({
    queryKey: ["labels", "bulk", ids],
    queryFn: () => getBulkItemLabelBundles(ids, token),
    enabled: token !== null && ids.length > 0,
    staleTime: 60_000,
  })
  const [qrUrls, setQrUrls] = useState<Record<string, string>>({})
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfFailed, setPdfFailed] = useState(false)

  useEffect(() => {
    if (!labels.data) {
      setQrUrls({})
      return
    }

    const nextUrls: Record<string, string> = {}
    for (const item of labels.data.items) {
      nextUrls[item.itemId] = URL.createObjectURL(item.qrBlob)
    }
    setQrUrls(nextUrls)

    return () => {
      for (const url of Object.values(nextUrls)) URL.revokeObjectURL(url)
    }
  }, [labels.data])

  if (ids.length === 0) {
    return (
      <section className="space-y-6 p-6">
        <p className="text-sm text-muted-foreground">{t("items.labels.empty")}</p>
        <Button asChild variant="outline">
          <Link href="/items">{t("items.labels.backToItems")}</Link>
        </Button>
      </section>
    )
  }

  if (labels.isLoading) {
    return (
      <section className="space-y-6 p-6">
        <Skeleton className="h-40 w-full max-w-3xl" />
      </section>
    )
  }

  const printableItems = labels.data?.items ?? []
  const skippedCount = labels.data?.skippedCount ?? 0

  async function handleDownloadPdf() {
    if (!token || printableItems.length === 0) return
    setPdfFailed(false)
    setPdfLoading(true)
    try {
      const { blob, filename } = await getItemLabelsPdf(ids, token)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.download = filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch {
      setPdfFailed(true)
    } finally {
      setPdfLoading(false)
    }
  }

  return (
    <section className="space-y-6 p-6 print:space-y-0 print:p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div>
          <h1 className="text-2xl font-semibold">{t("items.labels.title")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("items.labels.summary", { count: printableItems.length })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/items">
              <ArrowLeft className="h-4 w-4" />
              {t("items.labels.backToItems")}
            </Link>
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={handleDownloadPdf}
            disabled={printableItems.length === 0 || pdfLoading}
          >
            <FileDown className="h-4 w-4" />
            {t("items.labels.downloadPdf")}
          </Button>
          <Button type="button" onClick={() => window.print()} disabled={printableItems.length === 0}>
            <Printer className="h-4 w-4" />
            {t("items.detail.print")}
          </Button>
        </div>
      </div>

      {pdfFailed ? (
        <p className="text-sm text-destructive print:hidden">
          {t("items.labels.downloadFailed")}
        </p>
      ) : null}

      {skippedCount > 0 ? (
        <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm text-muted-foreground print:hidden">
          {t("items.labels.skipped", { count: skippedCount })}
        </p>
      ) : null}

      {printableItems.length === 0 ? (
        <p className="text-sm text-muted-foreground print:hidden">{t("items.labels.notFound")}</p>
      ) : (
        <div className="grid justify-start gap-4 [grid-template-columns:repeat(auto-fill,minmax(6cm,6cm))] print:block">
          {printableItems.map((item) => {
            const qrUrl = qrUrls[item.itemId]
            return (
              <div
                key={item.itemId}
                className="box-border flex min-h-[4cm] w-[6cm] break-inside-avoid flex-col items-center justify-center gap-1.5 rounded-[0.25rem] border border-black/20 bg-white p-2 text-center text-black print:inline-flex print:rounded-none print:border print:border-black/20"
              >
                {qrUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={qrUrl}
                    alt={`QR code for ${item.label.name}`}
                    className="h-[2.65cm] w-[2.65cm]"
                  />
                ) : (
                  <div className="h-[2.65cm] w-[2.65cm] rounded-[0.25rem] bg-neutral-100" />
                )}
                <div className="w-full truncate text-[0.75rem] font-semibold leading-tight">
                  {item.label.name}
                </div>
                <div className="w-full truncate text-[0.6rem] text-neutral-600">
                  #{item.label.item_id.slice(0, 8)} · x{item.label.quantity}
                </div>
                {item.label.barcode ? (
                  <>
                    {/* Phase 37：條碼圖（Code128）；不可編碼時只留下方文字 */}
                    <LabelBarcode value={item.label.barcode} />
                    <div className="w-full truncate font-mono text-[0.6rem]">
                      {item.label.barcode}
                    </div>
                  </>
                ) : null}
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
