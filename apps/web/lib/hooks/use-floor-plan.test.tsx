import { act, renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"
import { useUpdateFloorPlan } from "./use-locations"
import { updateLocation } from "@/lib/api/locations"

vi.mock("@/lib/auth/use-auth", () => ({ useAccessToken: () => "jwt" }))
vi.mock("@/lib/api/locations", () => ({ updateLocation: vi.fn() }))
const region = { x: 0.1, y: 0.2, w: 0.3, h: 0.4 }

describe("平面圖樂觀 PATCH", () => {
  it("同步樹與清單；失敗還原移除圖片連帶清除的區域", async () => {
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    const rows = [
      { id: 1, parent_id: null, floor_plan_image_id: "image" },
      { id: 2, parent_id: 1, plan_region: region },
    ]
    const tree = [{ ...rows[0], children: [{ ...rows[1], children: [] }] }]
    qc.setQueryData(["locations"], rows)
    qc.setQueryData(["locations", "tree"], tree)
    let reject!: (e: Error) => void
    vi.mocked(updateLocation).mockImplementation(
      () =>
        new Promise((_resolve, fail) => {
          reject = fail
        }),
    )
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    )
    const { result } = renderHook(() => useUpdateFloorPlan(), { wrapper })
    act(() => result.current.mutate({ id: 1, body: { floor_plan_image_id: null } }))
    await waitFor(() =>
      expect(qc.getQueryData(["locations"])).toEqual([
        { ...rows[0], floor_plan_image_id: null },
        { ...rows[1], plan_region: null },
      ]),
    )
    expect(qc.getQueryData(["locations", "tree"])).toEqual([
      {
        ...tree[0],
        floor_plan_image_id: null,
        children: [{ ...tree[0]!.children[0], plan_region: null }],
      },
    ])
    act(() => reject(new Error("offline")))
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(qc.getQueryData(["locations"])).toEqual(rows)
    expect(qc.getQueryData(["locations", "tree"])).toEqual(tree)
  })
})

it("設定區域立即反映到兩份快取，成功後保留", async () => {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  const child = { id: 2, parent_id: 1, plan_region: null }
  qc.setQueryData(["locations"], [child])
  qc.setQueryData(["locations", "tree"], [{ id: 1, children: [{ ...child, children: [] }] }])
  let resolve!: (value: never) => void
  vi.mocked(updateLocation).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done
      }),
  )
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  const { result } = renderHook(() => useUpdateFloorPlan(), { wrapper })
  act(() => result.current.mutate({ id: 2, body: { plan_region: region } }))
  await waitFor(() =>
    expect(qc.getQueryData(["locations"])).toEqual([{ ...child, plan_region: region }]),
  )
  expect(qc.getQueryData(["locations", "tree"])).toEqual([
    { id: 1, children: [{ ...child, plan_region: region, children: [] }] },
  ])
  act(() => resolve({ ...child, plan_region: region } as never))
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(qc.getQueryData(["locations"])).toEqual([{ ...child, plan_region: region }])
})
