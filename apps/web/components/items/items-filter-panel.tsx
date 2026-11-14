"use client"

import { useTranslations } from "next-intl"

import { LocationSelect } from "@/components/locations/location-select"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { ItemFilters } from "@/lib/api/items"
import { useCategories } from "@/lib/hooks/use-categories"
import { useLocations } from "@/lib/hooks/use-locations"
import { useTags } from "@/lib/hooks/use-tags"

interface Props {
  filters: ItemFilters
  onChange: (next: ItemFilters) => void
}

export function ItemsFilterPanel({ filters, onChange }: Props) {
  const t = useTranslations()
  const cats = useCategories()
  const locs = useLocations()
  const tags = useTags()

  const anyActive =
    filters.categoryId != null || filters.locationId != null ||
    (filters.tagIds && filters.tagIds.length > 0)

  const flatCats: Array<{ id: number; label: string }> = []
  const walk = (nodes: typeof cats.data, depth = 0) => {
    if (!nodes) return
    for (const n of nodes) {
      flatCats.push({ id: n.id, label: `${"— ".repeat(depth)}${n.name}` })
      walk(n.children ?? [], depth + 1)
    }
  }
  walk(cats.data)

  return (
    <div className="space-y-3 border rounded-md p-3 text-sm">
      <div>
        <Label>{t("items.form.category")}</Label>
        <Select
          value={filters.categoryId?.toString() ?? "all"}
          onValueChange={(v) =>
            onChange({ ...filters, categoryId: v === "all" ? undefined : Number(v), page: 1 })
          }
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("items.form.noneOption")}</SelectItem>
            {flatCats.map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>{c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>{t("items.form.location")}</Label>
        <LocationSelect
          value={filters.locationId ?? null}
          onChange={(id) =>
            onChange({ ...filters, locationId: id ?? undefined, page: 1 })
          }
          nodes={locs.data ?? []}
          label={t("items.form.location")}
          testId="filter-location-select"
        />
        {filters.locationId != null ? (
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            <Checkbox
              checked={filters.locationScope === "exact"}
              onCheckedChange={(checked) =>
                onChange({
                  ...filters,
                  locationScope: checked === true ? "exact" : undefined,
                  page: 1,
                })
              }
              aria-label={t("items.filter.onlyThisLevel")}
            />
            {t("items.filter.onlyThisLevel")}
          </label>
        ) : null}
      </div>

      <div>
        <Label>{t("items.form.tags")}</Label>
        <div className="flex flex-wrap gap-1">
          {(tags.data ?? []).map((tag) => {
            const on = filters.tagIds?.includes(tag.id) ?? false
            return (
              <button
                key={tag.id}
                type="button"
                onClick={() => {
                  const next = on
                    ? (filters.tagIds ?? []).filter((id) => id !== tag.id)
                    : [...(filters.tagIds ?? []), tag.id]
                  onChange({ ...filters, tagIds: next.length ? next : undefined, page: 1 })
                }}
                className={`rounded-sm px-2 py-0.5 text-xs ${on ? "bg-primary text-primary-foreground" : "bg-muted"}`}
              >
                {tag.name}
              </button>
            )
          })}
        </div>
      </div>

      {anyActive && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange({ q: filters.q, page: 1 })}
        >
          {t("items.list.clearFilters")}
        </Button>
      )}
    </div>
  )
}
