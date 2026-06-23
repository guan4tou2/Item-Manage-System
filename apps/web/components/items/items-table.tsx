"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { ItemRead } from "@/lib/api/items"

interface ItemsTableProps {
  items: ItemRead[]
  selectedIds?: string[]
  onSelectionChange?: (ids: string[]) => void
  getRowDisabled?: (item: ItemRead) => boolean
}

export function ItemsTable({
  items,
  selectedIds,
  onSelectionChange,
  getRowDisabled,
}: ItemsTableProps) {
  const t = useTranslations()
  const selectionEnabled = selectedIds !== undefined && onSelectionChange !== undefined
  const selectedSet = new Set(selectedIds ?? [])
  const selectableIds = items
    .filter((item) => !getRowDisabled?.(item))
    .map((item) => item.id)
  const selectedSelectableIds = selectableIds.filter((id) => selectedSet.has(id))
  const allSelected = selectableIds.length > 0 && selectedSelectableIds.length === selectableIds.length
  const someSelected = selectedSelectableIds.length > 0 && !allSelected
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
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((i) => {
          const rowDisabled = Boolean(getRowDisabled?.(i))
          const selected = selectedSet.has(i.id)
          const categoryLabel = t("items.list.columnCategory")
          const locationLabel = t("items.list.columnLocation")
          const nameLabel = t("items.list.columnName")
          const quantityLabel = t("items.list.columnQuantity")
          const tagsLabel = t("items.list.columnTags")
          return (
            <TableRow
              key={i.id}
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
                <Link className="font-medium underline-offset-2 hover:underline" href={`/items/${i.id}`}>
                  {i.name}
                </Link>
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
                {i.location ? [i.location.floor, i.location.room, i.location.zone].filter(Boolean).join(" / ") : "—"}
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
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
