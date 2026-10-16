import type { Route } from "next"

export interface SettingsPageDef {
  /** i18n key under `settings.index.pages.<id>` */
  id: string
  href: Route
  adminOnly?: boolean
}

export interface SettingsGroupDef {
  /** i18n key under `settings.index.groups.<id>` */
  id: string
  pages: readonly SettingsPageDef[]
}

/** 設定頁資訊架構（roadmap §5.2）；首層群組 ≤4、每群組頁面 ≤6。 */
export const SETTINGS_GROUPS: readonly SettingsGroupDef[] = [
  {
    id: "personal",
    pages: [
      { id: "profile", href: "/settings/profile" as Route },
      { id: "password", href: "/settings/password" as Route },
      { id: "preferences", href: "/settings/preferences" as Route },
    ],
  },
  {
    id: "notifications",
    pages: [
      { id: "channels", href: "/settings/channels" as Route },
      { id: "notifications", href: "/settings/notifications" as Route },
      { id: "reminders", href: "/settings/reminders" as Route },
    ],
  },
  {
    id: "integrations",
    pages: [
      { id: "webhooks", href: "/settings/webhooks" as Route },
      { id: "tokens", href: "/settings/tokens" as Route },
      { id: "data", href: "/settings/data" as Route },
      { id: "customization", href: "/settings/customization" as Route },
      { id: "taxonomy", href: "/settings/taxonomy" as Route },
    ],
  },
  {
    id: "admin",
    pages: [
      { id: "members", href: "/settings/members" as Route, adminOnly: true },
      { id: "audit", href: "/settings/audit" as Route, adminOnly: true },
    ],
  },
]
