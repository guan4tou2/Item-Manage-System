import { fireEvent, render, screen, within } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { NotificationPreferencesResponse } from "@/lib/api/notification-preferences"
import enMessages from "@/messages/en.json"

import { NotificationPreferencesPanel } from "./notification-preferences-panel"

const mocks = vi.hoisted(() => ({
  query: {
    data: undefined as unknown,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  },
  updateMutate: vi.fn(),
  resetMutate: vi.fn(),
}))

vi.mock("@/lib/hooks/use-notification-preferences", () => ({
  useNotificationPreferences: () => mocks.query,
  useUpdateNotificationPreferences: () => ({
    mutate: mocks.updateMutate,
    isPending: false,
  }),
  useResetNotificationPreferences: () => ({
    mutate: mocks.resetMutate,
    isPending: false,
  }),
}))

const t = enMessages.settings.notificationPreferences

const CHANNELS = ["in_app", "email", "line", "telegram", "web_push"] as const

const TYPES = [
  { key: "low_stock", group: "items", locked: false },
  { key: "expiring_soon", group: "items", locked: false },
  { key: "expired", group: "items", locked: false },
  { key: "loan_open", group: "collab", locked: false },
  { key: "loan_overdue", group: "collab", locked: false },
  { key: "loan_returned", group: "collab", locked: false },
  { key: "transfer.request", group: "collab", locked: false },
  { key: "transfer.accepted", group: "collab", locked: false },
  { key: "group_invite", group: "collab", locked: true },
  { key: "report_ready", group: "system", locked: false },
  { key: "system", group: "system", locked: true },
] as const

/** 與後端預設一致：全開，唯 expired／expiring_soon 的外送管道預設關。 */
function snapshot(
  overrides: Partial<NotificationPreferencesResponse> = {},
): NotificationPreferencesResponse {
  const matrix = Object.fromEntries(
    TYPES.map((type) => [
      type.key,
      Object.fromEntries(
        CHANNELS.map((channel) => [
          channel,
          !(
            (type.key === "expired" || type.key === "expiring_soon") &&
            ["email", "line", "telegram"].includes(channel)
          ),
        ]),
      ),
    ]),
  )
  return {
    types: TYPES.map((type) => ({ ...type })),
    channels: [...CHANNELS],
    matrix,
    has_custom: false,
    channel_availability: {
      in_app: true,
      email: true,
      line: false,
      telegram: false,
      web_push: false,
    },
    ...overrides,
  }
}

function setQuery(overrides: Partial<typeof mocks.query> = {}) {
  mocks.query.data = snapshot()
  mocks.query.isLoading = false
  mocks.query.isError = false
  Object.assign(mocks.query, overrides)
}

function renderPanel() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <NotificationPreferencesPanel />
    </NextIntlClientProvider>,
  )
}

describe("NotificationPreferencesPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setQuery()
  })

  it("renders the three group cards with the desktop matrix and mobile cards", () => {
    renderPanel()

    expect(screen.getByText(t.groups.items)).toBeInTheDocument()
    expect(screen.getByText(t.groups.collab)).toBeInTheDocument()
    expect(screen.getByText(t.groups.system)).toBeInTheDocument()

    const matrix = screen.getByTestId("preferences-matrix-items")
    expect(within(matrix).getByRole("switch", { name: "Low stock: In-app" })).toBeChecked()
    expect(within(matrix).getByRole("switch", { name: "Expired: Email" })).not.toBeChecked()
    expect(within(matrix).getByRole("switch", { name: "Expired: In-app" })).toBeChecked()

    const cards = screen.getByTestId("preferences-cards-items")
    expect(within(cards).getByRole("switch", { name: "Low stock: Email" })).toBeChecked()
  })

  it("toggles a cell and calls the update mutation with the cell payload", () => {
    renderPanel()

    const cell = within(screen.getByTestId("preferences-matrix-items")).getByRole(
      "switch",
      { name: "Low stock: Email" },
    )
    fireEvent.click(cell)

    expect(mocks.updateMutate).toHaveBeenCalledWith([
      { type: "low_stock", channel: "email", enabled: false },
    ])
  })

  it("disables locked rows and labels them with the lock tooltip", () => {
    renderPanel()

    const matrix = screen.getByTestId("preferences-matrix-collab")
    expect(
      within(matrix).getByRole("switch", { name: "Group invite: In-app" }),
    ).toBeDisabled()
    expect(within(matrix).getAllByLabelText(t.lockedTooltip).length).toBeGreaterThan(0)
  })

  it("disables unbound channels and links to the channel settings", () => {
    renderPanel()

    const matrix = screen.getByTestId("preferences-matrix-items")
    expect(within(matrix).getByRole("switch", { name: "Low stock: LINE" })).toBeDisabled()
    expect(
      within(matrix).getByRole("switch", { name: "Low stock: In-app" }),
    ).toBeEnabled()

    const links = within(matrix).getAllByRole("link", { name: t.goLink })
    expect(links.length).toBeGreaterThan(0)
    expect(links[0]).toHaveAttribute("href", "/settings/channels")
  })

  it("shows the defaults banner and hides the reset button without custom overrides", () => {
    renderPanel()

    expect(screen.getByTestId("preferences-defaults-banner")).toBeInTheDocument()
    expect(screen.getByText(t.defaultsSummary)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: t.reset })).toBeNull()
  })

  it("shows the reset button with custom overrides and confirms the reset flow", async () => {
    setQuery({ data: snapshot({ has_custom: true }) })
    renderPanel()

    expect(screen.queryByTestId("preferences-defaults-banner")).toBeNull()

    fireEvent.click(screen.getByRole("button", { name: t.reset }))
    const dialog = await screen.findByRole("alertdialog")
    expect(within(dialog).getByText(t.resetTitle)).toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole("button", { name: t.resetConfirm }))
    expect(mocks.resetMutate).toHaveBeenCalledTimes(1)
  })

  it("shows skeletons while loading", () => {
    setQuery({ data: undefined, isLoading: true })
    renderPanel()

    expect(screen.getByLabelText(t.loading)).toBeInTheDocument()
    expect(screen.queryByText(t.groups.items)).toBeNull()
  })

  it("shows a retryable error state when loading fails", () => {
    setQuery({ data: undefined, isError: true })
    renderPanel()

    expect(screen.getByText(t.loadError)).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: t.retry }))
    expect(mocks.query.refetch).toHaveBeenCalledTimes(1)
  })
})
