import type { ItemFilters } from "@/lib/api/items"

export function filtersFromSearchParams(params: URLSearchParams): ItemFilters {
  const f: ItemFilters = {}
  const q = params.get("q")
  if (q) f.q = q
  const cat = params.get("category")
  if (cat) {
    const n = Number(cat)
    if (!Number.isNaN(n)) f.categoryId = n
  }
  const loc = params.get("location")
  if (loc) {
    const n = Number(loc)
    if (!Number.isNaN(n)) f.locationId = n
  }
  const tags = params.get("tags")
  if (tags) {
    f.tagIds = tags.split(",").filter(Boolean).map(Number).filter((n) => !Number.isNaN(n))
    if (f.tagIds.length === 0) delete f.tagIds
  }
  const page = params.get("page")
  if (page) f.page = Math.max(1, Number(page))
  return f
}

export function filtersToSearchParams(f: ItemFilters): URLSearchParams {
  const p = new URLSearchParams()
  if (f.q) p.set("q", f.q)
  if (f.categoryId != null) p.set("category", String(f.categoryId))
  if (f.locationId != null) p.set("location", String(f.locationId))
  if (f.tagIds && f.tagIds.length > 0) p.set("tags", f.tagIds.join(","))
  if (f.page && f.page > 1) p.set("page", String(f.page))
  return p
}
