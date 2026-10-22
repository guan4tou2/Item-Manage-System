import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import { apiFetch } from "@/lib/api/client"
import enMessages from "@/messages/en.json"

import { AuditLogPanel } from "./audit-log-panel"

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}))

const row = {
  id: "a1",
  user_id: "u12345678-0000-0000-0000-000000000000",
  user_email: "alice@test.io" as string | null,
  action: "item.create",
  resource_type: "item",
  resource_id: "r12345678-0000-0000-0000-000000000000",
  meta: null as Record<string, unknown> | null,
  created_at: "2026-10-01T10:00:00Z",
}

function envelope(overrides: Record<string, unknown> = {}) {
  return {
    items: [row],
    total: 1,
    limit: 50,
    offset: 0,
    facets: {
      actions: [
        { value: "item.create", count: 1 },
        { value: "admin.user.set_active", count: 3 },
      ],
      resource_types: [
        { value: "item", count: 1 },
        { value: "user", count: 3 },
      ],
    },
    ...overrides,
  }
}

function mockApi(handler?: (url: string) => unknown) {
  vi.mocked(apiFetch).mockImplementation((async (url: string) => {
    const body = handler ? handler(url) : envelope()
    return {
      json: async () => body,
      blob: async () => new Blob(["csv"], { type: "text/csv" }),
      headers: new Headers({
        "content-disposition": 'attachment; filename="audit-logs-20261023.csv"',
      }),
    } as unknown as Response
  }) as unknown as typeof apiFetch)
}

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <AuditLogPanel />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.hasPointerCapture = vi.fn()
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
})

const FIRST_PAGE = "/admin/audit-logs?limit=50&offset=0"

/** 表格與行動卡片會渲染相同文字 → 查詢列內容時限定在表格內。 */
async function findInTable(text: string | RegExp) {
  const table = await screen.findByTestId("audit-table")
  return within(table).findByText(text)
}

describe("AuditLogPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(URL, "createObjectURL", {
      value: vi.fn(() => "blob:audit"),
      writable: true,
      configurable: true,
    })
    Object.defineProperty(URL, "revokeObjectURL", {
      value: vi.fn(),
      writable: true,
      configurable: true,
    })
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {})
    mockApi()
  })

  it("loads the first page with default paging", async () => {
    renderPanel()

    expect(await findInTable("item.create")).toBeInTheDocument()
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(FIRST_PAGE, { accessToken: "jwt" })
    expect(screen.getByText("1 record(s)")).toBeInTheDocument()
    expect(screen.getByText("Page 1 of 1")).toBeInTheDocument()
  })

  it("shows the user email instead of the raw id", async () => {
    renderPanel()

    expect(await findInTable("alice@test.io")).toBeInTheDocument()
    const table = await screen.findByTestId("audit-table")
    expect(within(table).queryByText(/u1234567/)).not.toBeInTheDocument()
  })

  it("filters by action and resets to the first page", async () => {
    const user = userEvent.setup()
    mockApi((url) => envelope({ total: 120, offset: url.includes("offset=50") ? 50 : 0 }))
    renderPanel()

    await user.click(await screen.findByRole("button", { name: "Next" }))
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
        "/admin/audit-logs?limit=50&offset=50",
        { accessToken: "jwt" },
      ),
    )

    await user.click(screen.getByRole("combobox", { name: "Action" }))
    await user.click(await screen.findByRole("option", { name: /admin\.user\.set_active/ }))

    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
        "/admin/audit-logs?limit=50&offset=0&action=admin.user.set_active",
        { accessToken: "jwt" },
      ),
    )
  })

  it("debounces the keyword search", async () => {
    const user = userEvent.setup()
    renderPanel()
    await findInTable("item.create")

    await user.type(screen.getByLabelText("Search"), "alice")

    // 尚未超過 debounce 視窗 → 不應帶 q 請求
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalledWith(
      expect.stringContaining("q=alice"),
      expect.anything(),
    )

    await waitFor(
      () =>
        expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
          "/admin/audit-logs?limit=50&offset=0&q=alice",
          { accessToken: "jwt" },
        ),
      { timeout: 2000 },
    )
  })

  it("pages forward and back", async () => {
    const user = userEvent.setup()
    mockApi((url) => envelope({ total: 120, offset: url.includes("offset=50") ? 50 : 0 }))
    renderPanel()

    await user.click(await screen.findByRole("button", { name: "Next" }))
    expect(await screen.findByText("Page 2 of 3")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Previous" }))
    expect(await screen.findByText("Page 1 of 3")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled()
  })

  it("expands a row to show formatted meta json", async () => {
    const user = userEvent.setup()
    mockApi(() => envelope({ items: [{ ...row, meta: { role: "editor", n: 2 } }] }))
    renderPanel()

    const table = await screen.findByTestId("audit-table")
    await user.click(within(table).getByRole("button", { name: "Details" }))

    const pre = await screen.findByTestId("audit-meta-json")
    expect(pre.textContent).toContain('"role": "editor"')
  })

  it("hides the meta toggle when the row has no meta", async () => {
    renderPanel()

    await findInTable("item.create")
    const table = await screen.findByTestId("audit-table")
    expect(within(table).queryByRole("button", { name: "Details" })).not.toBeInTheDocument()
  })

  it("exports the current filters as csv", async () => {
    const user = userEvent.setup()
    renderPanel()
    await findInTable("item.create")

    await user.click(screen.getByRole("button", { name: "Export CSV" }))

    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/admin/audit-logs/export.csv", {
        accessToken: "jwt",
      }),
    )
    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalled()
  })

  it("distinguishes no data from no matches", async () => {
    const user = userEvent.setup()
    mockApi((url) =>
      url.includes("action=") ? envelope({ items: [], total: 0 }) : envelope(),
    )
    renderPanel()
    await findInTable("item.create")

    await user.click(screen.getByRole("combobox", { name: "Action" }))
    await user.click(await screen.findByRole("option", { name: /item\.create/ }))

    expect(await screen.findByText("No records match the filters")).toBeInTheDocument()
  })

  it("shows an alert with retry when loading fails", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    renderPanel()

    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent("Failed to load audit logs")
    expect(within(alert).getByRole("button", { name: "Retry" })).toBeInTheDocument()
  })

  it("renders mobile cards alongside the table", async () => {
    renderPanel()

    await findInTable("item.create")
    expect(screen.getAllByTestId("audit-card").length).toBeGreaterThan(0)
  })

  it("clears filters and restores the unfiltered page", async () => {
    const user = userEvent.setup()
    mockApi((url) =>
      url.includes("q=alice")
        ? envelope({ items: [{ ...row, action: "search.result" }], total: 1 })
        : envelope(),
    )
    renderPanel()
    await findInTable("item.create")

    const input = screen.getByLabelText("Search")
    await user.type(input, "alice")
    expect(await findInTable("search.result")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Clear filters" }))

    expect(input).toHaveValue("")
    // 第一頁資料仍在 staleTime 內 → 直接回快取，不重新請求
    expect(await findInTable("item.create")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Clear filters" })).toBeDisabled()
  })

})
