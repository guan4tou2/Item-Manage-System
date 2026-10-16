import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

import enMessages from "@/messages/en.json"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/notification-preferences", () => ({
  getNotificationPreferences: vi.fn(),
  updateNotificationPreferences: vi.fn(),
  resetNotificationPreferences: vi.fn(),
}))

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

import * as api from "@/lib/api/notification-preferences"
import {
  notificationPreferencesQueryKey,
  useNotificationPreferences,
  useResetNotificationPreferences,
  useUpdateNotificationPreferences,
} from "./use-notification-preferences"

let queryClient: QueryClient

function wrapper({ children }: { children: ReactNode }) {
  return (
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </NextIntlClientProvider>
  )
}

function snapshot(
  overrides: Partial<api.NotificationPreferencesResponse> = {},
): api.NotificationPreferencesResponse {
  return {
    types: [{ key: "low_stock", group: "items", locked: false }],
    channels: ["in_app", "email", "line", "telegram", "web_push"],
    matrix: {
      low_stock: {
        in_app: true,
        email: true,
        line: true,
        telegram: true,
        web_push: true,
      },
    },
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

describe("use-notification-preferences", () => {
  beforeEach(() => {
    auth.token = "jwt"
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
  })

  it("fetches the snapshot with the access token", async () => {
    vi.mocked(api.getNotificationPreferences).mockResolvedValue(snapshot())

    const { result } = renderHook(() => useNotificationPreferences(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.getNotificationPreferences).toHaveBeenCalledWith("jwt")
  })

  it("does not fetch without a token", () => {
    auth.token = null

    renderHook(() => useNotificationPreferences(), { wrapper })

    expect(api.getNotificationPreferences).not.toHaveBeenCalled()
  })

  it("applies the toggle optimistically, then replaces with the server snapshot", async () => {
    const initial = snapshot()
    queryClient.setQueryData(notificationPreferencesQueryKey, initial)

    let resolveUpdate!: (value: api.NotificationPreferencesResponse) => void
    vi.mocked(api.updateNotificationPreferences).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveUpdate = resolve
        }),
    )

    const { result } = renderHook(() => useUpdateNotificationPreferences(), { wrapper })
    result.current.mutate([{ type: "low_stock", channel: "email", enabled: false }])

    await waitFor(() => {
      const cached = queryClient.getQueryData<api.NotificationPreferencesResponse>(
        notificationPreferencesQueryKey,
      )
      expect(cached?.matrix.low_stock?.email).toBe(false)
      expect(cached?.has_custom).toBe(true)
    })

    const server = snapshot({
      has_custom: true,
      matrix: {
        low_stock: {
          in_app: true,
          email: false,
          line: true,
          telegram: true,
          web_push: false,
        },
      },
    })
    resolveUpdate(server)

    await waitFor(() => {
      expect(queryClient.getQueryData(notificationPreferencesQueryKey)).toEqual(server)
    })
    expect(vi.mocked(toast.success)).toHaveBeenCalled()
  })

  it("rolls back the optimistic change and toasts on error", async () => {
    const initial = snapshot()
    queryClient.setQueryData(notificationPreferencesQueryKey, initial)
    vi.mocked(api.updateNotificationPreferences).mockRejectedValue(new Error("boom"))

    const { result } = renderHook(() => useUpdateNotificationPreferences(), { wrapper })
    result.current.mutate([{ type: "low_stock", channel: "email", enabled: false }])

    await waitFor(() => expect(vi.mocked(toast.error)).toHaveBeenCalled())
    expect(queryClient.getQueryData(notificationPreferencesQueryKey)).toEqual(initial)
  })

  it("reset replaces the cache with the server snapshot", async () => {
    queryClient.setQueryData(
      notificationPreferencesQueryKey,
      snapshot({ has_custom: true }),
    )
    const fresh = snapshot()
    vi.mocked(api.resetNotificationPreferences).mockResolvedValue(fresh)

    const { result } = renderHook(() => useResetNotificationPreferences(), { wrapper })
    result.current.mutate()

    await waitFor(() => {
      expect(queryClient.getQueryData(notificationPreferencesQueryKey)).toEqual(fresh)
    })
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Reset to defaults")
  })
})
