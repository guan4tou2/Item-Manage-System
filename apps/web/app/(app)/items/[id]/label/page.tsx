"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useItemLabel, useItemQrObjectUrl } from "@/lib/hooks/use-label"

export default function ItemLabelPage() {
  const t = useTranslations()
  const params = useParams<{ id: string }>()
  const id = params?.id ?? ""
  const label = useItemLabel(id)
  const qrUrl = useItemQrObjectUrl(id)

  if (label.isLoading) {
    return (
      <section className="space-y-4 p-6">
        <Skeleton className="h-64 w-full max-w-md" />
      </section>
    )
  }
  if (label.isError || !label.data) {
    return (
      <section className="space-y-4 p-6">
        <p className="text-muted-foreground">{t("items.detail.notFound")}</p>
      </section>
    )
  }
  const data = label.data

  return (
    <section className="space-y-6 p-6 print:space-y-0 print:p-0">
      <div className="flex items-center gap-2 print:hidden">
        <Button asChild variant="outline">
          <Link href={`/items/${id}` as never}>返回物品</Link>
        </Button>
        <Button onClick={() => window.print()}>列印</Button>
      </div>

      {/*
        The label box below is what prints. Sized for a ~6x4cm sticker.
        CSS `break-inside: avoid` keeps it from splitting across pages.
      */}
      <div
        className="mx-auto box-border flex w-[6cm] flex-col items-center gap-2 break-inside-avoid rounded border border-black/20 bg-white p-2 text-center text-black print:mx-0 print:border-0"
        style={{ minHeight: "4cm" }}
      >
        {qrUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={qrUrl}
            alt={`QR code for ${data.name}`}
            className="h-[3.2cm] w-[3.2cm]"
          />
        ) : (
          <Skeleton className="h-[3.2cm] w-[3.2cm]" />
        )}
        <div className="w-full truncate text-[0.75rem] font-semibold leading-tight">
          {data.name}
        </div>
        <div className="w-full truncate text-[0.6rem] text-muted-foreground">
          #{data.item_id.slice(0, 8)} · x{data.quantity}
        </div>
      </div>
    </section>
  )
}
