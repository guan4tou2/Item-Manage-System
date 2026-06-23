"use client"

import Link from "next/link"
import { ListPlus, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import type { LowStockItem } from "@/lib/api/stats"
import { createRestockListFromLowStockItems } from "@/lib/api/lists"
import { useAccessToken } from "@/lib/auth/use-auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  items: LowStockItem[]
  loading?: boolean
}

export function LowStockCard({ items, loading }: Props) {
  const t = useTranslations()
  const router = useRouter()
  const token = useAccessToken()
  const [creating, setCreating] = useState(false)

  const createRestockList = async () => {
    setCreating(true)
    try {
      const date = new Date().toISOString().slice(0, 10)
      const list = await createRestockListFromLowStockItems(items, token, {
        title: t("dashboard.lowStock.restockListTitle", { date }),
      })
      toast.success(t("dashboard.lowStock.restockCreated"))
      router.push(`/lists/${list.id}` as never)
    } catch {
      toast.error(t("dashboard.lowStock.restockFailed"))
    } finally {
      setCreating(false)
    }
  }

  return (
    <Card>
      <CardHeader className="gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle className="text-base">{t("dashboard.lowStock.title")}</CardTitle>
        {!loading && items.length > 0 ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={createRestockList}
            disabled={creating}
            className="w-full justify-center sm:w-auto"
          >
            {creating ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <ListPlus className="h-4 w-4" aria-hidden />
            )}
            {creating
              ? t("dashboard.lowStock.creatingRestockList")
              : t("dashboard.lowStock.createRestockList")}
          </Button>
        ) : null}
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
