import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import SettingsRemindersPage from "./page"

vi.mock("@/components/settings/reminders-panel", () => ({
  RemindersPanel: () => <div data-testid="reminders-panel" />,
}))

describe("SettingsRemindersPage", () => {
  it("renders the shell title and mounts the reminders panel", () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <SettingsRemindersPage />
      </NextIntlClientProvider>,
    )

    expect(
      screen.getByRole("heading", {
        name: enMessages.settings.index.pages.reminders.title,
      }),
    ).toBeInTheDocument()
    expect(screen.getByTestId("reminders-panel")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: enMessages.settings.title })).toHaveAttribute(
      "href",
      "/settings",
    )
  })
})
