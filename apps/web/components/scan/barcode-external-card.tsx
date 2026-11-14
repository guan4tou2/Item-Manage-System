"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import { EditableOnly } from "@/components/common/editable-only"
import { Button } from "@/components/ui/button"
import type { BarcodeLookup } from "@/lib/api/barcodes"

interface Props {
  result: BarcodeLookup
  onRetry: () => void
}

/**
 * 外查結果三態（§5.4）：ok（來源標註＋帶入新增）／not_found（查無公開資料）／
 * unavailable（網路不穩＋重試，與查無區分）／unsupported（無對應 provider）。
 */
export function BarcodeExternalCard({ result, onRetry }: Props) {
  const t = useTranslations()
  const createHref = `/items/new?barcode=${encodeURIComponent(result.code)}` as never

  if (result.external_status === "ok" && result.external) {
    const external = result.external
    const sourceLabel =
      external.source === "openfoodfacts"
        ? t("scan.external.sourceNames.openfoodfacts")
        : external.source === "openlibrary"
          ? t("scan.external.sourceNames.openlibrary")
          : external.source
    return (
      <div data-testid="barcode-external-card" className="space-y-3 rounded-[0.25rem] border p-3">
        <p
          data-testid="barcode-external-source"
          className="text-xs text-muted-foreground"
        >
          {t("scan.external.source", { source: sourceLabel })}
        </p>
        <div className="flex gap-3">
          {external.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={external.image_url}
              alt=""
              className="h-16 w-16 shrink-0 rounded-[0.25rem] object-cover"
            />
          ) : null}
          <div className="min-w-0">
            <p className="text-sm font-medium">{external.name}</p>
            {external.description ? (
              <p className="mt-1 text-xs text-muted-foreground">
                {external.description}
              </p>
            ) : null}
          </div>
        </div>
        <EditableOnly>
          <Button asChild>
            <Link href={createHref}>{t("scan.external.bringToNew")}</Link>
          </Button>
        </EditableOnly>
      </div>
    )
  }

  if (result.external_status === "not_found") {
    return (
      <div data-testid="barcode-external-card" className="space-y-3 rounded-[0.25rem] border p-3">
        <p className="text-sm">{t("scan.external.notFound")}</p>
        <Button asChild variant="outline">
          <Link href={createHref}>{t("scan.external.createWithBarcode")}</Link>
        </Button>
      </div>
    )
  }

  if (result.external_status === "unavailable") {
    return (
      <div data-testid="barcode-external-card" className="space-y-3 rounded-[0.25rem] border p-3">
        <p className="text-sm">{t("scan.external.unavailable")}</p>
        <div className="flex flex-wrap gap-2">
          <Button onClick={onRetry}>{t("scan.lookup.retry")}</Button>
          <Button asChild variant="outline">
            <Link href={createHref}>{t("scan.external.stillCreate")}</Link>
          </Button>
        </div>
      </div>
    )
  }

  // unsupported（或未知狀態）：僅提供以條碼新增
  return (
    <div data-testid="barcode-external-card" className="space-y-3 rounded-[0.25rem] border p-3">
      <p className="text-sm">{t("scan.external.unsupported")}</p>
      <Button asChild variant="outline">
        <Link href={createHref}>{t("scan.external.createWithBarcode")}</Link>
      </Button>
    </div>
  )
}
