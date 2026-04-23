"use client"

import { useMemo, useState } from "react"
import { useTranslations } from "next-intl"

import { KindBadge } from "@/components/lists/kind-badge"
import { ListCard } from "@/components/lists/list-card"
import { NewListDialog } from "@/components/lists/new-list-dialog"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useLists } from "@/lib/hooks/use-lists"
import type { ListKind, ListSummary } from "@/lib/api/lists"

const KINDS: ListKind[] = ["travel", "shopping", "collection", "generic"]

export default function ListsPage() {
  const t = useTranslations()
  const [filter, setFilter] = useState<ListKind | "all">("all")
  const query = useLists()

  const grouped = useMemo(() => {
    const all = query.data?.items ?? []
    const src = filter === "all" ? all : all.filter((r) => r.kind === filter)
    const map = new Map<ListKind, ListSummary[]>()
    for (const k of KINDS) map.set(k, [])
    for (const row of src) map.get(row.kind as ListKind)?.push(row)
    return map
  }, [query.data, filter])

  const isEmpty = (query.data?.items.length ?? 0) === 0

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("lists.title")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("lists.title")}</h1>
        <NewListDialog />
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={filter === "all" ? "default" : "outline"}
          onClick={() => setFilter("all")}
        >
          {t("lists.filter.all")}
        </Button>
        {KINDS.map((k) => (
          <Button
            key={k}
            size="sm"
            variant={filter === k ? "default" : "outline"}
            onClick={() => setFilter(k)}
          >
            {t(`lists.kind.${k}`)}
          </Button>
        ))}
      </div>

      {query.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : isEmpty ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded border border-dashed p-12 text-center">
          <p className="text-sm font-medium">{t("lists.empty.title")}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {KINDS.map((k) => {
            const rows = grouped.get(k) ?? []
            if (rows.length === 0) return null
            return (
              <div key={k} className="space-y-3">
                <div className="flex items-center gap-2">
                  <KindBadge kind={k} />
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {rows.map((row) => (
                    <ListCard key={row.id} row={row} />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
