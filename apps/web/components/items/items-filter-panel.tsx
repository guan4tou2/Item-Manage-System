"use client"

import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
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

      <div>
        <Label>{t("items.form.location")}</Label>
        <Select
          value={filters.locationId?.toString() ?? "all"}
          onValueChange={(v) =>
            onChange({ ...filters, locationId: v === "all" ? undefined : Number(v), page: 1 })
          }
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("items.form.noneOption")}</SelectItem>
            {(locs.data ?? []).map((l) => (
              <SelectItem key={l.id} value={String(l.id)}>
                {[l.floor, l.room, l.zone].filter(Boolean).join(" / ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
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
                className={`rounded px-2 py-0.5 text-xs ${on ? "bg-primary text-primary-foreground" : "bg-muted"}`}
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
