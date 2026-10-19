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
  const scope = params.get("location_scope")
  if (scope === "exact") f.locationScope = "exact"
  const tags = params.get("tags")
  if (tags) {
    f.tagIds = tags.split(",").filter(Boolean).map(Number).filter((n) => !Number.isNaN(n))
    if (f.tagIds.length === 0) delete f.tagIds
  }
  const page = params.get("page")
  if (page) f.page = Math.max(1, Number(page))
  const expiry = params.get("expiry")
  if (expiry === "expired" || expiry === "expiring_soon") f.expiry = expiry
  const loan = params.get("loan")
  if (loan === "borrowed" || loan === "overdue") f.loan = loan
  const minQuantity = params.get("min_quantity")
  if (minQuantity !== null && !Number.isNaN(Number(minQuantity))) {
    f.minQuantity = Number(minQuantity)
  }
  const maxQuantity = params.get("max_quantity")
  if (maxQuantity !== null && !Number.isNaN(Number(maxQuantity))) {
    f.maxQuantity = Number(maxQuantity)
  }
  const sort = params.get("sort")
  if (sort === "expiry_asc" || sort === "name_asc" || sort === "created_desc") {
    f.sort = sort
  }
  return f
}

export function filtersToSearchParams(f: ItemFilters): URLSearchParams {
  const p = new URLSearchParams()
  if (f.q) p.set("q", f.q)
  if (f.categoryId != null) p.set("category", String(f.categoryId))
  if (f.locationId != null) p.set("location", String(f.locationId))
  if (f.locationId != null && f.locationScope === "exact") {
    p.set("location_scope", "exact")
  }
  if (f.tagIds && f.tagIds.length > 0) p.set("tags", f.tagIds.join(","))
  if (f.expiry) p.set("expiry", f.expiry)
  if (f.loan) p.set("loan", f.loan)
  if (f.minQuantity != null) p.set("min_quantity", String(f.minQuantity))
  if (f.maxQuantity != null) p.set("max_quantity", String(f.maxQuantity))
  if (f.sort) p.set("sort", f.sort)
  if (f.page && f.page > 1) p.set("page", String(f.page))
  return p
}
