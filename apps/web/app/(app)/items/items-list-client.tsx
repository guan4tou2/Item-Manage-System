"use client"

import type { Route } from "next"
import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useTranslations } from "next-intl"
import { useCallback, useEffect, useMemo, useState } from "react"

import { ItemsFilterPanel } from "@/components/items/items-filter-panel"
import { ItemsTable } from "@/components/items/items-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import type { ItemFilters } from "@/lib/api/items"
import { useItems } from "@/lib/hooks/use-items"
import { filtersFromSearchParams, filtersToSearchParams } from "@/lib/items/filters"

export function ItemsListClient() {
  const t = useTranslations()
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const filters = useMemo<ItemFilters>(
    () => filtersFromSearchParams(new URLSearchParams(params.toString())),
    [params],
  )

  const [searchInput, setSearchInput] = useState(filters.q ?? "")
  useEffect(() => setSearchInput(filters.q ?? ""), [filters.q])

  const writeFilters = useCallback(
    (next: ItemFilters) => {
      const qs = filtersToSearchParams(next).toString()
      const href = (qs ? `${pathname}?${qs}` : pathname) as Route
      router.replace(href, { scroll: false })
    },
    [router, pathname],
  )

  useEffect(() => {
    const h = setTimeout(() => {
      if (searchInput !== (filters.q ?? "")) {
        writeFilters({ ...filters, q: searchInput || undefined, page: 1 })
      }
    }, 300)
    return () => clearTimeout(h)
  }, [searchInput, filters, writeFilters])

  const { data, isLoading } = useItems(filters)

  return (
    <div className="grid gap-4 md:grid-cols-[16rem_1fr]">
      <aside className="space-y-3">
        <ItemsFilterPanel filters={filters} onChange={writeFilters} />
      </aside>

      <section className="space-y-3">
        <div className="flex gap-2">
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t("items.list.searchPlaceholder")}
            aria-label={t("items.list.searchPlaceholder")}
          />
          <Button asChild>
            <Link href="/items/new">{t("items.list.new")}</Link>
          </Button>
        </div>

        {isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : !data || data.items.length === 0 ? (
          <div className="rounded border p-6 text-center text-muted-foreground">
            {data && data.total === 0 && !filters.q && !filters.categoryId && !filters.locationId && !filters.tagIds ? (
              <>
                <p>{t("items.list.empty")}</p>
                <Button asChild variant="link">
                  <Link href="/items/new">{t("items.list.emptyCta")}</Link>
                </Button>
              </>
            ) : (
              <p>{t("items.list.noResults")}</p>
            )}
          </div>
        ) : (
          <>
            <ItemsTable items={data.items} />
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{t("items.list.page", {
                page: data.page,
                total: Math.max(1, Math.ceil(data.total / data.per_page)),
              })}</span>
              <div className="flex gap-2">
                <Button
                  variant="outline" size="sm"
                  aria-label={t("items.list.previousPage")}
                  disabled={data.page <= 1}
                  onClick={() => writeFilters({ ...filters, page: Math.max(1, (filters.page ?? 1) - 1) })}
                >
                  ←
                </Button>
                <Button
                  variant="outline" size="sm"
                  aria-label={t("items.list.nextPage")}
                  disabled={data.page * data.per_page >= data.total}
                  onClick={() => writeFilters({ ...filters, page: (filters.page ?? 1) + 1 })}
                >
                  →
                </Button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
