import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { LocationTreeNode } from "@/lib/api/locations"
import en from "@/messages/en.json"
import { FloorPlan } from "./floor-plan"

const mocks = vi.hoisted(() => ({
  tree: vi.fn(),
  mutate: vi.fn(),
  readonly: false,
  imageError: false,
  retry: vi.fn(),
}))
vi.mock("@/lib/hooks/use-locations", () => ({
  useLocationTree: () => mocks.tree(),
  useUpdateFloorPlan: () => ({ mutateAsync: mocks.mutate, isPending: false }),
}))
vi.mock("@/lib/auth/use-auth", () => ({ useAccessToken: () => "jwt" }))
vi.mock("@/lib/auth/use-readonly", () => ({ useReadOnly: () => mocks.readonly }))
vi.mock("@/components/common/auth-image", () => ({
  AuthImage: ({
    fallback,
    onLoad,
    alt,
  }: {
    fallback: React.ReactNode
    onLoad: () => void
    alt: string
  }) => (mocks.imageError ? fallback : <button onClick={onLoad}>{alt}</button>),
}))
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }))
const room = (id: number, name: string, region = true): LocationTreeNode => ({
  id,
  name,
  parent_id: 1,
  path: name,
  sort_order: 0,
  item_count: 1,
  plan_region: region ? { x: 0.1, y: 0.2, w: 0.3, h: 0.4 } : null,
  children: [],
})
const makeFloor = (): LocationTreeNode => ({
  ...room(1, "1F", false),
  parent_id: null,
  floor_plan_image_id: "image",
  item_count: 0,
  children: [{ ...room(2, "Kitchen"), children: [room(4, "Shelf")] }, room(3, "Living", false)],
})
let floor: LocationTreeNode
const renderPlan = () =>
  render(
    <NextIntlClientProvider locale="en" messages={en}>
      <FloorPlan locationId={1} />
    </NextIntlClientProvider>,
  )
const load = () => fireEvent.click(screen.getByRole("button", { name: "Floor plan for 1F" }))
beforeEach(() => {
  vi.clearAllMocks()
  mocks.readonly = false
  mocks.imageError = false
  floor = makeFloor()
  mocks.tree.mockImplementation(() => ({
    data: [floor],
    isLoading: false,
    isError: false,
    refetch: mocks.retry,
  }))
  mocks.mutate.mockResolvedValue({})
})

describe("平面圖旅程與狀態", () => {
  it("區域為真實連結、包含子孫數量，未放置子位置也有清單入口", () => {
    renderPlan()
    load()
    const links = screen.getAllByRole("link", { name: "Kitchen, 2 items" })
    expect(links).toHaveLength(2)
    for (const link of links) expect(link).toHaveAttribute("href", "/items?location=2")
    expect(screen.getByRole("link", { name: "Living, 1 items" })).toHaveAttribute(
      "href",
      "/items?location=3",
    )
    expect(screen.getByText("Not placed")).toBeInTheDocument()
  })
  it("viewer 可看可點，沒有編輯或圖片管理入口", () => {
    mocks.readonly = true
    renderPlan()
    load()
    expect(screen.getAllByRole("link", { name: "Kitchen, 2 items" })).toHaveLength(2)
    for (const name of [
      "Edit regions",
      "Replace floor plan",
      "Remove floor plan",
      "Upload floor plan",
    ])
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument()
  })
  it("載入佔位", () => {
    mocks.tree.mockReturnValue({ isLoading: true })
    renderPlan()
    expect(screen.getByRole("status", { name: "Loading floor plan" })).toBeInTheDocument()
  })
  it("沒有平面圖時 writer 有上傳入口，viewer 僅顯示說明", () => {
    floor.floor_plan_image_id = null
    const view = renderPlan()
    expect(screen.getByText("No floor plan yet")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Upload floor plan" })).toBeInTheDocument()
    mocks.readonly = true
    view.rerender(
      <NextIntlClientProvider locale="en" messages={en}>
        <FloorPlan locationId={1} />
      </NextIntlClientProvider>,
    )
    expect(screen.queryByRole("button", { name: "Upload floor plan" })).not.toBeInTheDocument()
  })
  it("沒有子位置仍顯示圖片及回樹入口", () => {
    floor.children = []
    renderPlan()
    expect(screen.getByText("Add child locations before marking regions")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to locations" })).toHaveAttribute(
      "href",
      "/locations",
    )
  })
  it("沒有區域可開始標示", () => {
    floor.children![0]!.plan_region = null
    renderPlan()
    expect(screen.getByText("No regions marked yet")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Start marking" }))
    expect(screen.getByRole("button", { name: "Select child location Living" })).toBeInTheDocument()
  })
  it("樹錯誤可重試", () => {
    mocks.tree.mockReturnValue({ isError: true, refetch: mocks.retry })
    renderPlan()
    expect(screen.getByText("Could not load locations")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Retry" }))
    expect(mocks.retry).toHaveBeenCalled()
  })
  it("不存在的位置有 404 說明", () => {
    mocks.tree.mockReturnValue({ data: [] })
    renderPlan()
    expect(screen.getByText("Location not found (404)")).toBeInTheDocument()
  })
  it("圖片失敗仍可由清單導覽，且提供重試", () => {
    mocks.imageError = true
    renderPlan()
    expect(screen.getByText("Could not load floor plan")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Kitchen, 2 items" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument()
  })
  it("編輯模式提供鍵盤調整、清除區域，且不再導覽", () => {
    renderPlan()
    load()
    fireEvent.click(screen.getByRole("button", { name: "Edit regions" }))
    const region = screen.getByRole("button", { name: "Kitchen, 2 items" })
    fireEvent.click(region)
    fireEvent.keyDown(region, { key: "ArrowRight", shiftKey: true })
    expect(mocks.mutate).toHaveBeenCalledWith({
      id: 2,
      body: { plan_region: { x: 0.1, y: 0.2, w: 0.31, h: 0.4 } },
    })
    fireEvent.click(screen.getByRole("button", { name: "Clear region Kitchen" }))
    expect(mocks.mutate).toHaveBeenLastCalledWith({ id: 2, body: { plan_region: null } })
  })
  it("移除前說明會清除全部子位置區域", () => {
    renderPlan()
    fireEvent.click(screen.getByRole("button", { name: "Remove floor plan" }))
    expect(
      screen.getByText("This clears regions for all direct child locations."),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Remove floor plan" }))
    expect(mocks.mutate).toHaveBeenCalledWith({ id: 1, body: { floor_plan_image_id: null } })
  })
})
