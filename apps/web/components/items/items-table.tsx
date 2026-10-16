"use client"

import { truncatePath } from "@/lib/locations/tree"
import { ChevronDown, ChevronRight, Minus } from "lucide-react"
import Link from "next/link"
import { useTranslations } from "next-intl"
import { Fragment, useState } from "react"

import { ExpiryBadge } from "./expiry-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { ItemRead } from "@/lib/api/items"
import { useBatches } from "@/lib/hooks/use-batches"

interface ItemsTableProps {
  items: ItemRead[]
  selectedIds?: string[]
  onSelectionChange?: (ids: string[]) => void
  getRowDisabled?: (item: ItemRead) => boolean
  /** 到期模式（§5.5）：行內 −1 與批次展開。 */
  expiryMode?: boolean
  onConsumeOne?: (item: ItemRead) => void
}

export function ItemsTable({
  items,
  selectedIds,
  onSelectionChange,
  getRowDisabled,
  expiryMode = false,
  onConsumeOne,
}: ItemsTableProps) {
  const t = useTranslations()
  const [expandedIds, setExpandedIds] = useState<string[]>([])
  const selectionEnabled = selectedIds !== undefined && onSelectionChange !== undefined
  const selectedSet = new Set(selectedIds ?? [])
  const selectableIds = items
    .filter((item) => !getRowDisabled?.(item))
    .map((item) => item.id)
  const selectedSelectableIds = selectableIds.filter((id) => selectedSet.has(id))
  const allSelected = selectableIds.length > 0 && selectedSelectableIds.length === selectableIds.length
  const someSelected = selectedSelectableIds.length > 0 && !allSelected
  const columnCount = 5 + (selectionEnabled ? 1 : 0) + (expiryMode ? 1 : 0)
  const mobileCellClass =
    "grid grid-cols-[minmax(5rem,40%)_1fr] items-start gap-3 px-4 py-3 text-sm before:text-xs before:font-medium before:text-muted-foreground before:content-[attr(data-label)] md:table-cell md:px-4 md:py-4 md:before:content-none"

  const updateSelection = (ids: string[]) => {
    onSelectionChange?.(Array.from(new Set(ids)))
  }

  const toggleItem = (id: string, checked: boolean) => {
    if (checked) {
      updateSelection([...(selectedIds ?? []), id])
      return
    }
    updateSelection((selectedIds ?? []).filter((selectedId) => selectedId !== id))
  }

  const toggleAll = (checked: boolean) => {
    if (checked) {
      updateSelection([...(selectedIds ?? []), ...selectableIds])
      return
    }
    updateSelection((selectedIds ?? []).filter((selectedId) => !selectableIds.includes(selectedId)))
  }

  const toggleExpanded = (id: string) => {
    setExpandedIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]))
  }

  return (
    <Table className="block min-w-0 border-separate border-spacing-0 md:table">
      <TableHeader className="sr-only md:table-header-group">
        <TableRow>
          {selectionEnabled ? (
            <TableHead className="w-10">
              <Checkbox
                aria-label={t("items.list.selectAll")}
                checked={allSelected ? true : someSelected ? "indeterminate" : false}
                disabled={selectableIds.length === 0}
                onCheckedChange={(checked) => toggleAll(checked === true)}
              />
            </TableHead>
          ) : null}
          <TableHead>{t("items.list.columnName")}</TableHead>
          <TableHead>{t("items.list.columnCategory")}</TableHead>
          <TableHead>{t("items.list.columnLocation")}</TableHead>
          <TableHead className="text-right">{t("items.list.columnQuantity")}</TableHead>
          <TableHead>{t("items.list.columnTags")}</TableHead>
          {expiryMode ? <TableHead>{t("items.list.columnActions")}</TableHead> : null}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((i) => {
          const rowDisabled = Boolean(getRowDisabled?.(i))
          const selected = selectedSet.has(i.id)
          const expanded = expandedIds.includes(i.id)
          const categoryLabel = t("items.list.columnCategory")
          const locationLabel = t("items.list.columnLocation")
          const nameLabel = t("items.list.columnName")
          const quantityLabel = t("items.list.columnQuantity")
          const tagsLabel = t("items.list.columnTags")
          const actionsLabel = t("items.list.columnActions")
          return (
            <Fragment key={i.id}>
              <TableRow
                className="mb-3 block rounded-md border bg-card transition-colors last:mb-0 md:table-row md:rounded-none md:border-x-0 md:border-t-0 md:bg-transparent"
                data-state={selected ? "selected" : undefined}
              >
                {selectionEnabled ? (
                  <TableCell className="flex justify-end px-4 pb-0 pt-4 md:table-cell md:w-10 md:p-4">
                    <Checkbox
                      aria-label={t("items.list.selectItem", { name: i.name })}
                      checked={selected}
                      disabled={rowDisabled}
                      onCheckedChange={(checked) => toggleItem(i.id, checked === true)}
                    />
                  </TableCell>
                ) : null}
                <TableCell
                  className={`${mobileCellClass} min-w-0 md:min-w-40`}
                  data-label={nameLabel}
                  data-testid="items-table-name-cell"
                >
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <Link
                      className="font-medium underline-offset-2 hover:underline"
                      href={`/items/${i.id}`}
                    >
                      {i.name}
                    </Link>
                    {i.track_batches && i.soonest_expiry ? (
                      <ExpiryBadge date={i.soonest_expiry} fallback="none" />
                    ) : null}
                  </div>
                </TableCell>
                <TableCell
                  className={mobileCellClass}
                  data-label={categoryLabel}
                  data-testid="items-table-category-cell"
                >
                  {i.category?.name ?? "—"}
                </TableCell>
                <TableCell
                  className={`${mobileCellClass} break-words`}
                  data-label={locationLabel}
                  data-testid="items-table-location-cell"
                >
                  {i.location ? (
                    <span title={i.location.path}>{truncatePath(i.location.path)}</span>
                  ) : (
                    "—"
                  )}
                </TableCell>
                <TableCell
                  className={`${mobileCellClass} text-right tabular-nums md:text-right`}
                  data-label={quantityLabel}
                  data-testid="items-table-quantity-cell"
                >
                  {i.quantity}
                </TableCell>
                <TableCell
                  className={`${mobileCellClass} min-w-0`}
                  data-label={tagsLabel}
                  data-testid="items-table-tags-cell"
                >
                  <div className="flex min-w-0 flex-wrap gap-1 md:inline-flex">
                  {i.tags.map((tag) => <Badge key={tag.id} variant="secondary">{tag.name}</Badge>)}
                  </div>
                </TableCell>
                {expiryMode ? (
                  <TableCell
                    className={`${mobileCellClass} md:w-32`}
                    data-label={actionsLabel}
                    data-testid="items-table-actions-cell"
                  >
                    {i.track_batches ? (
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          aria-expanded={expanded}
                          aria-label={
                            expanded
                              ? t("items.list.collapseBatches")
                              : t("items.list.expandBatches")
                          }
                          onClick={() => toggleExpanded(i.id)}
                        >
                          {expanded ? (
                            <ChevronDown className="h-4 w-4" aria-hidden="true" />
                          ) : (
                            <ChevronRight className="h-4 w-4" aria-hidden="true" />
                          )}
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          className="h-11 min-w-11 px-3"
                          aria-label={t("items.list.consumeOneAria", { name: i.name })}
                          disabled={i.quantity <= 0}
                          onClick={() => onConsumeOne?.(i)}
                        >
                          <Minus className="h-4 w-4" aria-hidden="true" />1
                        </Button>
                      </div>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                ) : null}
              </TableRow>
              {expiryMode && expanded ? (
                <TableRow className="mb-3 block rounded-md border border-t-0 bg-card md:table-row md:rounded-none md:border-x-0 md:border-t-0 md:bg-transparent">
                  <TableCell
                    colSpan={columnCount}
                    className="block px-4 pb-3 pt-0 md:table-cell"
                    data-testid="items-table-batches-cell"
                  >
                    <div className="rounded-md border bg-muted/30 p-3">
                      <ItemBatchesPreview itemId={i.id} />
                    </div>
                  </TableCell>
                </TableRow>
              ) : null}
            </Fragment>
          )
        })}
      </TableBody>
    </Table>
  )
}

function ItemBatchesPreview({ itemId }: { itemId: string }) {
  const t = useTranslations()
  const batches = useBatches(itemId)

  if (batches.isLoading) {
    return <Skeleton className="h-6 w-40" />
  }

  const active = (batches.data ?? []).filter(
    (batch) => batch.quantity > 0 && !batch.is_depleted,
  )
  if (active.length === 0) {
    return <p className="text-xs text-muted-foreground">{t("items.list.noActiveBatches")}</p>
  }

  return (
    <ul className="space-y-1">
      {active.map((batch) => (
        <li key={batch.id} className="flex flex-wrap items-center gap-2 text-xs">
          <span className="tabular-nums">
            {t("items.batches.remaining", { count: batch.quantity })}
          </span>
          {batch.expiry_date ? <ExpiryBadge date={batch.expiry_date} /> : null}
          {batch.note ? <span className="text-muted-foreground">{batch.note}</span> : null}
        </li>
      ))}
    </ul>
  )
}
