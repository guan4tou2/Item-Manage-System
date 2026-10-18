import type { Route } from "next"

export type NavKey =
  | "dashboard"
  | "items"
  | "stocktakes"
  | "categories"
  | "locations"
  | "scan"
  | "statistics"
  | "reports"
  | "notifications"
  | "lists"
  | "collab"
  | "settings"

export interface NavItem {
  key: NavKey
  href: Route
  /** i18n key for label */
  labelKey: string
}

/** 首層導覽（桌面橫列／行動 drawer 群組共同來源）；維持 11 項（D8）。 */
export const NAV_ITEMS: readonly NavItem[] = [
  { key: "dashboard", href: "/dashboard", labelKey: "nav.dashboard" },
  { key: "items", href: "/items", labelKey: "nav.items" },
  { key: "scan", href: "/scan" as Route, labelKey: "nav.scan" },
  { key: "stocktakes", href: "/stocktakes" as Route, labelKey: "nav.stocktakes" },
  { key: "categories", href: "/categories" as Route, labelKey: "nav.categories" },
  { key: "locations", href: "/locations" as Route, labelKey: "nav.locations" },
  { key: "statistics", href: "/statistics", labelKey: "nav.statistics" },
  { key: "notifications", href: "/notifications", labelKey: "nav.notifications" },
  { key: "lists", href: "/lists", labelKey: "nav.lists" },
  { key: "collab", href: "/collaboration", labelKey: "nav.collab" },
  { key: "settings", href: "/settings", labelKey: "nav.settings" },
]

const STATISTICS_ITEM: NavItem = {
  key: "statistics",
  href: "/statistics",
  labelKey: "nav.statistics",
}

const REPORTS_ITEM: NavItem = {
  key: "reports",
  href: "/reports" as Route,
  labelKey: "nav.reports",
}

/** 桌面「統計」下拉第二層（D8）。 */
export const STATS_MENU_ITEMS: readonly NavItem[] = [STATISTICS_ITEM, REPORTS_ITEM]

export type NavGroupId = "inventory" | "analysis" | "collab" | "system"

export interface NavGroup {
  id: NavGroupId
  /** i18n key under `nav.groups.<id>` */
  labelKey: string
  items: readonly NavItem[]
}

function pick(...keys: NavKey[]): NavItem[] {
  return keys.map((key) => {
    const item = NAV_ITEMS.find((candidate) => candidate.key === key)
    if (!item) throw new Error(`unknown nav key: ${key}`)
    return item
  })
}

/** 行動 drawer 的 4 群組（D8）：物品／分析／協作／系統。 */
export const NAV_GROUPS: readonly NavGroup[] = [
  {
    id: "inventory",
    labelKey: "nav.groups.inventory",
    items: pick("dashboard", "items", "scan", "stocktakes", "categories", "locations"),
  },
  {
    id: "analysis",
    labelKey: "nav.groups.analysis",
    items: [STATISTICS_ITEM, REPORTS_ITEM],
  },
  {
    id: "collab",
    labelKey: "nav.groups.collab",
    items: pick("notifications", "lists", "collab"),
  },
  {
    id: "system",
    labelKey: "nav.groups.system",
    items: pick("settings"),
  },
]
