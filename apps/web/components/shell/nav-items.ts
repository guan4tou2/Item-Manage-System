import type { Route } from "next"

export interface NavItem {
  key: "dashboard" | "items" | "statistics" | "lists" | "settings"
  href: Route
  /** i18n key for label */
  labelKey: string
}

export const NAV_ITEMS: readonly NavItem[] = [
  { key: "dashboard", href: "/dashboard", labelKey: "nav.dashboard" },
  { key: "items", href: "/items", labelKey: "nav.items" },
  { key: "statistics", href: "/statistics", labelKey: "nav.statistics" },
  { key: "lists", href: "/lists", labelKey: "nav.lists" },
  { key: "settings", href: "/settings", labelKey: "nav.settings" },
]
