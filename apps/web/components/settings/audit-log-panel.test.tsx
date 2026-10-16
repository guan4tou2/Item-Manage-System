import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

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
  action: "item.create",
  resource_type: "item",
  resource_id: "r12345678-0000-0000-0000-000000000000",
  meta: null,
  created_at: "2026-10-01T10:00:00Z",
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

describe("AuditLogPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiFetch).mockResolvedValue({
      json: async () => [row],
    } as unknown as Response)
  })

  it("loads and renders audit log rows", async () => {
    renderPanel()

    expect(await screen.findByText("item.create")).toBeInTheDocument()
    expect(screen.getByText(/r1234567/)).toBeInTheDocument()
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/admin/audit-logs?limit=200", {
      accessToken: "jwt",
    })
  })
})
