"use client"

import { Loader2, MapPin, Printer, Tags, Trash2, X } from "lucide-react"
import type { Route } from "next"
import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useTranslations } from "next-intl"
import { useCallback, useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

import { ItemsFilterPanel } from "@/components/items/items-filter-panel"
import { ItemsTable } from "@/components/items/items-table"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import type { ItemFilters } from "@/lib/api/items"
import { useBulkDeleteItems, useBulkUpdateItems, useItems } from "@/lib/hooks/use-items"
import { useLocations } from "@/lib/hooks/use-locations"
import { filtersFromSearchParams, filtersToSearchParams } from "@/lib/items/filters"

type TagMode = "replace" | "append"

function parseTagNames(value: string): string[] {
  const seen = new Set<string>()
  for (const part of value.split(/[,;\n]/)) {
    const tag = part.trim().toLowerCase()
    if (tag) seen.add(tag)
  }
  return Array.from(seen)
}

function formatLocation(location: { floor?: string | null; room?: string | null; zone?: string | null }) {
  return [location.floor, location.room, location.zone].filter(Boolean).join(" / ")
}

function labelsHref(itemIds: string[]): Route {
  const params = new URLSearchParams()
  for (const id of itemIds) params.append("ids", id)
  return `/items/labels?${params.toString()}` as Route
}

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
  const locations = useLocations()
  const bulkUpdate = useBulkUpdateItems()
  const bulkDelete = useBulkDeleteItems()
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [bulkTags, setBulkTags] = useState("")
  const [tagMode, setTagMode] = useState<TagMode>("replace")
  const [targetLocationId, setTargetLocationId] = useState("")

  useEffect(() => {
    if (!data) return
    const visibleIds = new Set(data.items.map((item) => item.id))
    setSelectedIds((ids) => ids.filter((id) => visibleIds.has(id)))
  }, [data])

  const selectedCount = selectedIds.length
  const bulkPending = bulkUpdate.isPending || bulkDelete.isPending

  const resetSelection = () => {
    setSelectedIds([])
    setBulkTags("")
    setTargetLocationId("")
  }

  const applyTags = async () => {
    const tagNames = parseTagNames(bulkTags)
    if (selectedIds.length === 0 || tagNames.length === 0) return
    try {
      await bulkUpdate.mutateAsync({
        item_ids: selectedIds,
        tag_names: tagNames,
        tag_mode: tagMode,
      })
      toast.success(t("items.bulk.tagsApplied", { count: selectedIds.length }))
      resetSelection()
    } catch {
      toast.error(t("items.bulk.actionFailed"))
    }
  }

  const moveLocation = async () => {
    if (selectedIds.length === 0 || !targetLocationId) return
    try {
      await bulkUpdate.mutateAsync({
        item_ids: selectedIds,
        location_id: Number(targetLocationId),
        tag_mode: "replace",
      })
      toast.success(t("items.bulk.locationMoved", { count: selectedIds.length }))
      resetSelection()
    } catch {
      toast.error(t("items.bulk.actionFailed"))
    }
  }

  const deleteSelected = async () => {
    if (selectedIds.length === 0) return
    try {
      await bulkDelete.mutateAsync({ item_ids: selectedIds })
      toast.success(t("items.bulk.deleted", { count: selectedIds.length }))
      resetSelection()
    } catch {
      toast.error(t("items.bulk.actionFailed"))
    }
  }

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
            {selectedCount > 0 ? (
              <div
                aria-busy={bulkPending}
                className="sticky bottom-3 z-20 rounded-md border bg-background/95 p-3 shadow-lg shadow-black/5 backdrop-blur supports-[backdrop-filter]:bg-background/85"
              >
                <div className="grid gap-3 xl:grid-cols-[auto_minmax(18rem,1fr)_minmax(14rem,18rem)_auto] xl:items-end">
                  <div className="flex items-center justify-between gap-3 xl:block">
                    <div>
                      <p className="text-sm font-medium">
                        {t("items.bulk.selectedCount", { count: selectedCount })}
                      </p>
                      <p className="text-xs text-muted-foreground">{t("items.bulk.selectionHint")}</p>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={resetSelection}
                      disabled={bulkPending}
                    >
                      <X className="h-4 w-4" />
                      {t("items.bulk.clear")}
                    </Button>
                  </div>

                  <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto_auto]">
                    <div className="space-y-1">
                      <Label htmlFor="bulk-tags" className="text-xs text-muted-foreground">
                        {t("items.bulk.tagsLabel")}
                      </Label>
                      <Input
                        id="bulk-tags"
                        value={bulkTags}
                        onChange={(event) => setBulkTags(event.target.value)}
                        placeholder={t("items.bulk.tagsPlaceholder")}
                        aria-label={t("items.bulk.tagsLabel")}
                        className="h-9"
                        disabled={bulkPending}
                      />
                    </div>
                    <div className="flex items-end gap-1">
                      <Button
                        type="button"
                        variant={tagMode === "replace" ? "secondary" : "outline"}
                        size="sm"
                        aria-pressed={tagMode === "replace"}
                        onClick={() => setTagMode("replace")}
                        disabled={bulkPending}
                      >
                        {t("items.bulk.replaceTags")}
                      </Button>
                      <Button
                        type="button"
                        variant={tagMode === "append" ? "secondary" : "outline"}
                        size="sm"
                        aria-pressed={tagMode === "append"}
                        onClick={() => setTagMode("append")}
                        disabled={bulkPending}
                      >
                        {t("items.bulk.appendTags")}
                      </Button>
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      className="self-end"
                      onClick={() => void applyTags()}
                      disabled={bulkPending || parseTagNames(bulkTags).length === 0}
                    >
                      {bulkUpdate.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Tags className="h-4 w-4" />}
                      {t("items.bulk.applyTags")}
                    </Button>
                  </div>

                  <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                    <div className="space-y-1">
                      <Label htmlFor="bulk-location" className="text-xs text-muted-foreground">
                        {t("items.bulk.moveTo")}
                      </Label>
                      <select
                        id="bulk-location"
                        value={targetLocationId}
                        onChange={(event) => setTargetLocationId(event.target.value)}
                        aria-label={t("items.bulk.moveTo")}
                        className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        disabled={bulkPending}
                      >
                        <option value="">{t("items.bulk.selectLocation")}</option>
                        {(locations.data ?? []).map((location) => (
                          <option key={location.id} value={location.id}>
                            {formatLocation(location)}
                          </option>
                        ))}
                      </select>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="self-end"
                      onClick={() => void moveLocation()}
                      disabled={bulkPending || !targetLocationId}
                    >
                      <MapPin className="h-4 w-4" />
                      {t("items.bulk.move")}
                    </Button>
                  </div>

                  <div className="flex flex-wrap gap-2 xl:justify-end">
                    <Button asChild variant="outline" size="sm">
                      <Link href={labelsHref(selectedIds)}>
                        <Printer className="h-4 w-4" />
                        {t("items.bulk.printLabels")}
                      </Link>
                    </Button>

                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button type="button" variant="destructive" size="sm" disabled={bulkPending}>
                          <Trash2 className="h-4 w-4" />
                          {t("items.bulk.deleteSelected")}
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>{t("items.bulk.confirmDeleteTitle")}</AlertDialogTitle>
                          <AlertDialogDescription>
                            {t("items.bulk.confirmDeleteBody", { count: selectedCount })}
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel disabled={bulkPending}>
                            {t("items.form.cancel")}
                          </AlertDialogCancel>
                          <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            disabled={bulkPending}
                            onClick={() => void deleteSelected()}
                          >
                            {bulkDelete.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                            {t("items.bulk.confirmDelete", { count: selectedCount })}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>
              </div>
            ) : null}

            <ItemsTable
              items={data.items}
              selectedIds={selectedIds}
              onSelectionChange={setSelectedIds}
            />
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
