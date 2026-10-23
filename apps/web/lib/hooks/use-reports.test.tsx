import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/reports", () => ({
  listReports: vi.fn(),
  getReport: vi.fn(),
}))

import * as api from "@/lib/api/reports"
import type { ReportListResponse, ReportRead } from "@/lib/api/reports"
import { useReport, useReports } from "./use-reports"

let queryClient: QueryClient

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const report: ReportRead = {
  id: "r1",
  kind: "monthly",
  period: "2026-09",
  generated_at: "2026-10-01T00:05:00Z",
  payload: {
    version: 1,
    kind: "monthly",
    period: "2026-09",
    timezone: "Asia/Taipei",
    period_start: "2026-09-01",
    period_end: "2026-09-30",
    generated_at: "2026-10-01T00:05:00Z",
    currency: "TWD",
    totals: { item_count: 42, quantity: 123 },
    activity: {
      items_created: 2,
      items_deleted: 0,
      quantity_in: 5,
      quantity_out: 3,
      loans_out: 1,
      loans_returned: 0,
      loans_overdue: 0,
    },
    expiry: { expiring_soon: 1, expired: 0 },
    valuation: {
      start: "1200.00",
      end: "1500.00",
      delta: "300.00",
      unpriced_items: 0,
    },
    top_categories: [{ label: "食品", count: 12 }],
    top_locations: [],
    has_activity: true,
  },
}

const list: ReportListResponse = {
  items: [report],
  total: 1,
  limit: 20,
  offset: 0,
}

describe("useReports / useReport", () => {
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.mocked(api.listReports).mockReset()
    vi.mocked(api.getReport).mockReset()
    auth.token = "jwt"
  })

  it("lists reports with the access token", async () => {
    vi.mocked(api.listReports).mockResolvedValue(list)

    const { result } = renderHook(() => useReports(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.listReports).toHaveBeenCalledWith({ limit: 20, offset: 0 }, "jwt")
    expect(result.current.data).toEqual(list)
  })

  it("does not list without a token", () => {
    auth.token = null

    renderHook(() => useReports(), { wrapper })

    expect(api.listReports).not.toHaveBeenCalled()
  })

  it("fetches a report detail by id", async () => {
    vi.mocked(api.getReport).mockResolvedValue(report)

    const { result } = renderHook(() => useReport("r1"), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.getReport).toHaveBeenCalledWith("r1", "jwt")
    expect(result.current.data?.payload.totals.item_count).toBe(42)
  })

  it("does not fetch a detail without an id", () => {
    renderHook(() => useReport(""), { wrapper })

    expect(api.getReport).not.toHaveBeenCalled()
  })
})
