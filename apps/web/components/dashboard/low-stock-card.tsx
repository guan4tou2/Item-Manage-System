"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import type { LowStockItem } from "@/lib/api/stats"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  items: LowStockItem[]
  loading?: boolean
}

export function LowStockCard({ items, loading }: Props) {
  const t = useTranslations()
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.lowStock.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.lowStock.loading")}</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.lowStock.empty")}</p>
        ) : (
          <ul className="divide-y">
            {items.map((row) => (
              <li
                key={row.item_id}
                className="flex items-center justify-between py-2"
              >
                <Link
                  href={`/items/${row.item_id}` as never}
                  className="truncate hover:underline"
                >
                  {row.name}
                </Link>
                <span className="ml-2 flex-shrink-0 text-sm">
                  <span className="font-semibold text-destructive">
                    {row.quantity}
                  </span>
                  <span className="text-muted-foreground"> / {row.min_quantity}</span>
                  <span className="ml-2 rounded bg-destructive/10 px-1.5 py-0.5 text-xs text-destructive">
                    -{row.deficit}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
