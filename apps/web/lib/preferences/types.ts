import type { paths } from "@ims/api-types"

export type PreferencesRead =
  paths["/api/users/me/preferences"]["get"]["responses"]["200"]["content"]["application/json"]

export type PreferencesUpdate =
  paths["/api/users/me/preferences"]["put"]["requestBody"]["content"]["application/json"]

export type ThemePreference = "system" | "light" | "dark"
