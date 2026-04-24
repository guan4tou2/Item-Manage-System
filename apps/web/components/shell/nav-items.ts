import type { Route } from "next"

export interface NavItem {
  key:
    | "dashboard"
    | "items"
    | "categories"
    | "locations"
    | "scan"
    | "statistics"
    | "notifications"
    | "lists"
    | "collab"
    | "settings"
  href: Route
  /** i18n key for label */
  labelKey: string
}

export const NAV_ITEMS: readonly NavItem[] = [
  { key: "dashboard", href: "/dashboard", labelKey: "nav.dashboard" },
  { key: "items", href: "/items", labelKey: "nav.items" },
  { key: "scan", href: "/scan" as Route, labelKey: "nav.scan" },
  { key: "categories", href: "/categories" as Route, labelKey: "nav.categories" },
  { key: "locations", href: "/locations" as Route, labelKey: "nav.locations" },
  { key: "statistics", href: "/statistics", labelKey: "nav.statistics" },
  { key: "notifications", href: "/notifications", labelKey: "nav.notifications" },
  { key: "lists", href: "/lists", labelKey: "nav.lists" },
  { key: "collab", href: "/collaboration", labelKey: "nav.collab" },
  { key: "settings", href: "/settings", labelKey: "nav.settings" },
]
