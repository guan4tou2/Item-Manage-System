"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"
import { Package } from "lucide-react"

import { imageUrl } from "@/lib/api/images"
import type { BarcodeLocalMatch } from "@/lib/api/barcodes"

interface Props {
  matches: BarcodeLocalMatch[]
}

/** 內查多筆命中：縮圖＋名稱＋位置路徑＋數量（§5.4 掃碼 SUCCESS）。 */
export function BarcodeCandidates({ matches }: Props) {
  const t = useTranslations()
  if (matches.length === 0) return null

  return (
    <div data-testid="barcode-candidates" className="rounded border p-3">
      <p className="mb-2 text-sm font-medium">
        {t("scan.candidates.title", { count: matches.length })}
      </p>
      <ul className="space-y-1">
        {matches.map((match) => (
          <li key={match.id}>
            <Link
              href={`/items/${match.id}` as never}
              className="flex items-center gap-3 rounded p-2 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
            >
              {match.image_id ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={imageUrl(match.image_id)}
                  alt=""
                  className="h-10 w-10 shrink-0 rounded object-cover"
                />
              ) : (
                <span
                  aria-hidden
                  className="grid h-10 w-10 shrink-0 place-items-center rounded bg-muted text-muted-foreground"
                >
                  <Package className="h-5 w-5" />
                </span>
              )}
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">
                  {match.name}
                </span>
                <span className="block truncate text-xs text-muted-foreground">
                  {match.location_path ?? t("scan.candidates.noLocation")}
                </span>
              </span>
              <span className="shrink-0 text-xs text-muted-foreground">
                {t("scan.candidates.quantity", { count: match.quantity })}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
