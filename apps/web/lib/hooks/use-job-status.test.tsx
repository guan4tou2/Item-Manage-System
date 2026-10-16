import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/jobs", () => ({
  getJobStatus: vi.fn(),
}))

import * as api from "@/lib/api/jobs"
import type { JobStatus } from "@/lib/api/jobs"
import { useJobStatus } from "./use-job-status"

let queryClient: QueryClient

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const status: JobStatus = {
  job: "expiry-scan",
  thresholds: {
    stale_after_hours: 26,
    advance_days: [30, 7, 0],
    expired_stop_days: 14,
  },
  last_run: null,
  stale: true,
}

describe("useJobStatus", () => {
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.mocked(api.getJobStatus).mockReset()
    auth.token = "jwt"
  })

  it("fetches the job status with the access token", async () => {
    vi.mocked(api.getJobStatus).mockResolvedValue(status)

    const { result } = renderHook(() => useJobStatus("expiry-scan"), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.getJobStatus).toHaveBeenCalledWith("expiry-scan", "jwt")
    expect(result.current.data).toEqual(status)
  })

  it("does not fetch without a token", () => {
    auth.token = null

    renderHook(() => useJobStatus("expiry-scan"), { wrapper })

    expect(api.getJobStatus).not.toHaveBeenCalled()
  })
})
