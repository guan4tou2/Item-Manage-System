import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import SettingsNotificationsPage from "./page"

vi.mock("@/components/settings/notification-preferences-panel", () => ({
  NotificationPreferencesPanel: () => <div data-testid="preferences-panel" />,
}))

describe("SettingsNotificationsPage", () => {
  it("renders the shell title and mounts the preferences panel", () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <SettingsNotificationsPage />
      </NextIntlClientProvider>,
    )

    expect(
      screen.getByRole("heading", {
        name: enMessages.settings.index.pages.notifications.title,
      }),
    ).toBeInTheDocument()
    expect(screen.getByTestId("preferences-panel")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: enMessages.settings.title })).toHaveAttribute(
      "href",
      "/settings",
    )
  })
})
