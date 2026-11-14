import { useEffect, type ReactNode } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { useItems, useItem } from "@/lib/hooks/use-items"
import { useAuthStore } from "@/lib/auth/auth-store"
import { useOfflineState } from "./runtime"
import type { PendingItem } from "./storage"
import type { ItemRead } from "@/lib/api/items"

const original = { id: "item", name: "original", quantity: 2, track_batches: false, category: null, location: null, tags: [], updated_at: "original-version" } as unknown as ItemRead
const row: PendingItem = { client_id: "key", owner_user_id: "owner", kind: "update", item_id: "item", base_updated_at: "original-version", created_at: "today", status: "pending", error_code: null, attempts: 0, trackBatches: false, customFields: [], values: { name: "mine", quantity: 3, category_id: null, location_id: null, tag_names: [], custom_values: {} } }
function setup() {
  useAuthStore.setState({ user: { id: "owner" } as never, accessToken: "token" })
  useOfflineState.setState({ rows: [], error: null })
  const qc = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } })
  qc.setQueryData(["items", {}], { items: [original], total: 1, page: 1, per_page: 20 })
  qc.setQueryData(["items", "item"], original)
  return function Wrapper({ children }: { children: ReactNode }) { return <QueryClientProvider client={qc}>{children}</QueryClientProvider> }
}
afterEach(() => { useAuthStore.getState().clear(); useOfflineState.setState({ rows: [], error: null }) })
it("queued deletes hide from the list, discard restores them, and data identity stays stable between renders", async () => {
  const effect = vi.fn()
  const { result, rerender } = renderHook(() => {
    const query = useItems({})
    useEffect(() => { effect(query.data) }, [query.data])
    return query
  }, { wrapper: setup() })
  const first = result.current.data
  rerender()
  expect(result.current.data).toBe(first)
  expect(effect).toHaveBeenCalledTimes(1)
  act(() => useOfflineState.setState({ rows: [{ ...row, kind: "delete" }] }))
  await waitFor(() => expect(result.current.data?.items).toEqual([]))
  const hidden = result.current.data
  rerender()
  expect(result.current.data).toBe(hidden)
  act(() => useOfflineState.setState({ rows: [] }))
  await waitFor(() => expect(result.current.data?.items).toEqual([original]))
})
it("item reads overlay pending values and preserve the version; conflict viewing shows server data", () => {
  const { result, rerender } = renderHook(() => useItem("item"), { wrapper: setup() })
  act(() => useOfflineState.setState({ rows: [row] }))
  expect(result.current.data).toMatchObject({ name: "mine", quantity: 3, updated_at: "original-version" })
  const data = result.current.data
  rerender()
  expect(result.current.data).toBe(data)
  act(() => useOfflineState.setState({ rows: [{ ...row, status: "conflict" }] }))
  expect(result.current.data).toBe(original)
})
