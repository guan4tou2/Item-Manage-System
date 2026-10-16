import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import SettingsPage from "./page"

const mocks = vi.hoisted(() => ({
  me: vi.fn(),
  refetch: vi.fn(),
}))

vi.mock("@/lib/hooks/use-profile", () => ({
  useMe: mocks.me,
  useBootstrapAdmin: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const adminUser = { id: "u1", email: "admin@example.com", username: "admin", is_admin: true }
const memberUser = { id: "u2", email: "member@example.com", username: "member", is_admin: false }

function setMe(overrides: Record<string, unknown> = {}) {
  mocks.me.mockReturnValue({
    isLoading: false,
    isError: false,
    data: memberUser,
    refetch: mocks.refetch,
    ...overrides,
  })
}

function renderPage() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <SettingsPage />
    </NextIntlClientProvider>,
  )
}

const t = enMessages.settings

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setMe()
  })

  it("renders the four groups with working links for admins", () => {
    setMe({ data: adminUser })
    renderPage()

    expect(screen.getByText(t.index.groups.personal.title)).toBeInTheDocument()
    expect(screen.getByText(t.index.groups.notifications.title)).toBeInTheDocument()
    expect(screen.getByText(t.index.groups.integrations.title)).toBeInTheDocument()
    expect(screen.getByText(t.index.groups.admin.title)).toBeInTheDocument()

    expect(
      screen.getByRole("link", { name: new RegExp(t.index.pages.profile.title) }),
    ).toHaveAttribute("href", "/settings/profile")
    expect(
      screen.getByRole("link", { name: new RegExp(t.index.pages.taxonomy.title) }),
    ).toHaveAttribute("href", "/settings/taxonomy")
    expect(
      screen.getByRole("link", { name: new RegExp(t.index.pages.members.title) }),
    ).toHaveAttribute("href", "/settings/members")
    expect(
      screen.getByRole("link", { name: new RegExp(t.index.pages.audit.title) }),
    ).toHaveAttribute("href", "/settings/audit")
    expect(
      screen.getByRole("link", { name: new RegExp(t.index.pages.notifications.title) }),
    ).toHaveAttribute("href", "/settings/notifications")
  })

  it("hides the admin group and shows bootstrap guidance for non-admins", () => {
    renderPage()

    expect(screen.queryByText(t.index.groups.admin.title)).toBeNull()
    expect(
      screen.queryByRole("link", { name: new RegExp(t.index.pages.members.title) }),
    ).toBeNull()
    expect(screen.getByText(t.bootstrap.prompt)).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: new RegExp(t.index.pages.channels.title) }),
    ).toHaveAttribute("href", "/settings/channels")
  })

  it("shows skeleton cards while the profile query loads", () => {
    setMe({ isLoading: true, data: undefined })
    renderPage()

    expect(screen.getByLabelText(t.index.loading)).toBeInTheDocument()
    expect(screen.queryByText(t.index.groups.personal.title)).toBeNull()
  })

  it("shows a retryable error state when the profile query fails", () => {
    setMe({ isError: true, data: undefined })
    renderPage()

    expect(screen.getByText(t.index.loadError)).toBeInTheDocument()
    expect(screen.queryByText(t.index.groups.personal.title)).toBeNull()

    fireEvent.click(screen.getByRole("button", { name: t.index.retry }))
    expect(mocks.refetch).toHaveBeenCalledTimes(1)
  })
})
