import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"
import type { LocationTreeNode } from "@/lib/api/locations"

import { LocationsPanel } from "./locations-panel"

const hooks = vi.hoisted(() => ({
  tree: vi.fn(),
  flat: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  move: vi.fn(),
  remove: vi.fn(),
  bulk: vi.fn(),
}))

vi.mock("@/lib/hooks/use-locations", () => ({
  useLocationTree: () => hooks.tree(),
  useLocations: () => hooks.flat(),
  useCreateLocation: () => hooks.create(),
  useUpdateLocation: () => hooks.update(),
  useMoveLocation: () => hooks.move(),
  useDeleteLocation: () => hooks.remove(),
  useReorderLocations: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock("@/lib/hooks/use-items", () => ({
  useBulkUpdateItems: () => hooks.bulk(),
}))

const listItemsMock = vi.hoisted(() => vi.fn())
vi.mock("@/lib/api/items", () => ({
  listItems: (...args: unknown[]) => listItemsMock(...args),
}))

vi.mock("@/lib/hooks/use-is-mobile", () => ({ useIsMobile: () => false }))

const navMocks = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: navMocks.push }) }))

vi.mock("@/lib/auth/use-auth", () => ({ useAccessToken: () => "jwt" }))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

function node(
  id: number,
  name: string,
  parentId: number | null,
  children: LocationTreeNode[] = [],
  itemCount = 0,
  kind: string | null = null,
): LocationTreeNode {
  return {
    id,
    parent_id: parentId,
    name,
    kind,
    sort_order: 0,
    floor_plan_image_id: null,
    path: "",
    item_count: itemCount,
    children,
  } as LocationTreeNode
}

const treeData: LocationTreeNode[] = [
  node(1, "1F", null, [
    node(2, "Kitchen", 1, [node(4, "Top shelf", 2, [], 2), node(5, "Fridge", 2)], 1, "room"),
    node(3, "Living room", 1),
  ], 0, "floor"),
  node(6, "2F", null, [], 0, "floor"),
]

const flatData = [
  { id: 1, parent_id: null, name: "1F", kind: "floor", sort_order: 0, path: "1F" },
  { id: 2, parent_id: 1, name: "Kitchen", kind: "room", sort_order: 0, path: "1F / Kitchen" },
  { id: 4, parent_id: 2, name: "Top shelf", kind: null, sort_order: 0, path: "1F / Kitchen / Top shelf" },
  { id: 5, parent_id: 2, name: "Fridge", kind: null, sort_order: 1, path: "1F / Kitchen / Fridge" },
  { id: 3, parent_id: 1, name: "Living room", kind: null, sort_order: 1, path: "1F / Living room" },
  { id: 6, parent_id: null, name: "2F", kind: "floor", sort_order: 1, path: "2F" },
]

function stubHooks() {
  hooks.tree.mockReturnValue({ data: treeData, isLoading: false, isError: false, refetch: vi.fn() })
  hooks.flat.mockReturnValue({ data: flatData, isLoading: false })
  hooks.create.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
  hooks.update.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
  hooks.move.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
  hooks.remove.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue(undefined), isPending: false })
  hooks.bulk.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
  listItemsMock.mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20 })
}

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        {children}
      </NextIntlClientProvider>
    </QueryClientProvider>
  )
  return render(<LocationsPanel />, { wrapper })
}

// Radix Select 在 jsdom 需要 pointer capture／scrollIntoView polyfill
beforeAll(() => {
  Element.prototype.hasPointerCapture = vi.fn()
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
  Element.prototype.scrollIntoView = vi.fn()
})

beforeEach(() => {
  vi.clearAllMocks()
  stubHooks()
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  })
})

describe("LocationsPanel（位置標籤入口：Phase 36）", () => {
  it("節點選單可列印該位置標籤", async () => {
    const user = userEvent.setup()
    renderPanel()
    await user.click(within(screen.getByTestId("location-node-1")).getByRole("button", { name: "Expand" }))

    const kitchen = screen.getByTestId("location-node-2")
    await user.click(within(kitchen).getByRole("button", { name: /More actions for Kitchen/ }))
    await user.click(await screen.findByRole("menuitem", { name: "Print label" }))

    expect(navMocks.push).toHaveBeenCalledWith("/locations/labels?ids=2")
  })

  it("頁首有列印位置標籤入口（勾選模式）", async () => {
    const user = userEvent.setup()
    renderPanel()

    await user.click(screen.getByRole("button", { name: "Print location labels" }))

    expect(navMocks.push).toHaveBeenCalledWith("/locations/labels")
  })
})

describe("LocationsPanel（樹管理）", () => {
  it("renders roots collapsed and expands on demand", async () => {    const user = userEvent.setup()
    renderPanel()

    expect(screen.getByText("1F")).toBeInTheDocument()
    expect(screen.queryByText("Kitchen")).not.toBeInTheDocument()

    await user.click(within(screen.getByTestId("location-node-1")).getByRole("button", { name: "Expand" }))
    expect(screen.getByText("Kitchen")).toBeInTheDocument()

    await user.click(within(screen.getByTestId("location-node-1")).getByRole("button", { name: "Collapse" }))
    expect(screen.queryByText("Kitchen")).not.toBeInTheDocument()
  })

  it("shows direct item counts and the tree role", async () => {
    const user = userEvent.setup()
    renderPanel()
    await user.click(within(screen.getByTestId("location-node-1")).getByRole("button", { name: "Expand" }))
    await user.click(within(screen.getByTestId("location-node-2")).getByRole("button", { name: "Expand" }))

    expect(screen.getByRole("tree", { name: "Locations" })).toBeInTheDocument()
    const shelf = screen.getByTestId("location-node-4")
    expect(within(shelf).getByText("2 item(s)")).toBeInTheDocument()
    expect(shelf).toHaveAttribute("aria-level", "3")
    expect(screen.getByTestId("location-node-1")).toHaveAttribute("aria-expanded", "true")
  })

  it("renames a node with F2 and commits on Enter", async () => {
    const update = vi.fn().mockResolvedValue({})
    hooks.update.mockReturnValue({ mutateAsync: update, isPending: false })
    renderPanel()

    const user = userEvent.setup()
    await user.click(screen.getByTestId("location-node-1"))
    fireEvent.keyDown(screen.getByRole("tree"), { key: "F2" })

    const input = screen.getByLabelText("Rename")
    fireEvent.change(input, { target: { value: "Ground floor" } })
    fireEvent.keyDown(input, { key: "Enter" })

    await waitFor(() =>
      expect(update).toHaveBeenCalledWith({ id: 1, body: { name: "Ground floor" } }),
    )
  })

  it("adds a child node from the row menu", async () => {
    const create = vi.fn().mockResolvedValue({})
    hooks.create.mockReturnValue({ mutateAsync: create, isPending: false })
    renderPanel()

    const user = userEvent.setup()
    const floor = screen.getByTestId("location-node-1")
    await user.click(within(floor).getByRole("button", { name: /More actions for 1F/ }))
    await user.click(await screen.findByRole("menuitem", { name: "Add child" }))

    const input = screen.getByLabelText("Add child")
    fireEvent.change(input, { target: { value: "Bathroom" } })
    fireEvent.keyDown(input, { key: "Enter" })

    await waitFor(() =>
      expect(create).toHaveBeenCalledWith({ name: "Bathroom", parent_id: 1, sort_order: 0 }),
    )
  })

  it("blocks delete for a node with items and offers the move flow", async () => {
    const user = userEvent.setup()
    renderPanel()
    await user.click(within(screen.getByTestId("location-node-1")).getByRole("button", { name: "Expand" }))

    const kitchen = screen.getByTestId("location-node-2")
    await user.click(within(kitchen).getByRole("button", { name: /More actions for Kitchen/ }))
    await user.click(await screen.findByRole("menuitem", { name: "Delete" }))

    expect(
      await screen.findByText(/This location holds 1 item\(s\)/),
    ).toBeInTheDocument()
    expect(screen.getByText(/It has 2 child node\(s\)/)).toBeInTheDocument()
    expect(screen.getByTestId("delete-move-target")).toBeInTheDocument()

    const confirm = screen.getByRole("button", { name: "Delete" })
    expect(confirm).toBeDisabled()
  })

  it("moves the items of a blocked node to the chosen target", async () => {
    const bulk = vi.fn().mockResolvedValue({})
    hooks.bulk.mockReturnValue({ mutateAsync: bulk, isPending: false })
    listItemsMock.mockResolvedValue({
      items: [{ id: "item-1" }, { id: "item-2" }],
      total: 2,
      page: 1,
      per_page: 100,
    })
    const user = userEvent.setup()
    renderPanel()
    await user.click(within(screen.getByTestId("location-node-1")).getByRole("button", { name: "Expand" }))
    const kitchen = screen.getByTestId("location-node-2")
    await user.click(within(kitchen).getByRole("button", { name: /More actions for Kitchen/ }))
    await user.click(await screen.findByRole("menuitem", { name: "Delete" }))

    // 選目標：1F（cascading 第一層）
    await user.click(screen.getByLabelText("Move target 1"))
    await user.click(await screen.findByRole("option", { name: "1F" }))

    await user.click(screen.getByRole("button", { name: "Move 1 item(s)" }))

    await waitFor(() => expect(listItemsMock).toHaveBeenCalled())
    await waitFor(() =>
      expect(bulk).toHaveBeenCalledWith({
        item_ids: ["item-1", "item-2"],
        location_id: 1,
        tag_mode: "replace",
      }),
    )
  })

  it("deletes a clean node", async () => {
    const remove = vi.fn().mockResolvedValue(undefined)
    hooks.remove.mockReturnValue({ mutateAsync: remove, isPending: false })
    const user = userEvent.setup()
    renderPanel()

    const second = screen.getByTestId("location-node-6")
    await user.click(within(second).getByRole("button", { name: /More actions for 2F/ }))
    await user.click(await screen.findByRole("menuitem", { name: "Delete" }))

    const confirm = screen.getByRole("button", { name: "Delete" })
    expect(confirm).toBeEnabled()
    await user.click(confirm)

    await waitFor(() => expect(remove).toHaveBeenCalledWith(6))
  })

  it("marks invalid drag targets and only moves on valid drops", async () => {
    const move = vi.fn().mockResolvedValue({})
    hooks.move.mockReturnValue({ mutateAsync: move, isPending: false })
    const user = userEvent.setup()
    renderPanel()
    await user.click(within(screen.getByTestId("location-node-1")).getByRole("button", { name: "Expand" }))

    const floor = screen.getByTestId("location-node-1")
    const kitchen = screen.getByTestId("location-node-2")
    const living = screen.getByTestId("location-node-3")

    fireEvent.dragStart(floor)
    // 1F → 自己的子節點：非法（灰化＋tooltip）
    fireEvent.dragOver(kitchen)
    expect(kitchen).toHaveAttribute("data-drop-invalid", "true")
    expect(kitchen).toHaveAttribute("title", "Cannot move under itself or its own descendants")
    fireEvent.drop(kitchen)
    expect(move).not.toHaveBeenCalled()

    // 1F → 2F：合法（同層移動不成；改拖 Kitchen → 2F）
    fireEvent.dragStart(kitchen)
    fireEvent.dragOver(screen.getByTestId("location-node-6"))
    fireEvent.drop(screen.getByTestId("location-node-6"))

    // 僅一次移動：drop 不得冒泡到容器（否則會多送一次「搬到最上層」）
    await waitFor(() =>
      expect(move).toHaveBeenCalledWith({ id: 2, parentId: 6 }),
    )
    expect(move).toHaveBeenCalledTimes(1)
    expect(living).toBeInTheDocument()
  })

  it("moves a node to the top level when dropped on the tree container", async () => {
    const move = vi.fn().mockResolvedValue({})
    hooks.move.mockReturnValue({ mutateAsync: move, isPending: false })
    const user = userEvent.setup()
    renderPanel()
    await user.click(within(screen.getByTestId("location-node-1")).getByRole("button", { name: "Expand" }))

    const kitchen = screen.getByTestId("location-node-2")

    // 拖到容器空白（非任何列）＝移到最上層
    fireEvent.dragStart(kitchen)
    fireEvent.drop(screen.getByRole("tree"))

    await waitFor(() =>
      expect(move).toHaveBeenCalledWith({ id: 2, parentId: null }),
    )
    expect(move).toHaveBeenCalledTimes(1)
  })

  it("navigates with arrow keys and toggles with Enter", async () => {
    const user = userEvent.setup()
    renderPanel()
    const tree = screen.getByRole("tree")

    await user.click(screen.getByTestId("location-node-1"))
    fireEvent.keyDown(tree, { key: "ArrowDown" })
    expect(screen.getByTestId("location-node-6")).toHaveAttribute("tabindex", "0")

    fireEvent.keyDown(tree, { key: "ArrowUp" })
    expect(screen.getByTestId("location-node-1")).toHaveAttribute("tabindex", "0")

    fireEvent.keyDown(tree, { key: "ArrowRight" })
    expect(screen.getByText("Kitchen")).toBeInTheDocument()
  })

  it("offers creating a node when the search has no results", async () => {
    const create = vi.fn().mockResolvedValue({})
    hooks.create.mockReturnValue({ mutateAsync: create, isPending: false })
    renderPanel()

    fireEvent.change(screen.getByLabelText("Search locations (full paths shown)"), {
      target: { value: "Attic" },
    })

    const user = userEvent.setup()
    const button = await screen.findByRole("button", { name: 'Create new node “Attic”' })
    await user.click(button)

    await waitFor(() =>
      expect(create).toHaveBeenCalledWith({ name: "Attic", parent_id: null, sort_order: 0 }),
    )
  })

  it("shows a skeleton while loading, a retry on error, and an empty state", async () => {
    hooks.tree.mockReturnValue({ data: undefined, isLoading: true, isError: false, refetch: vi.fn() })
    const { unmount } = renderPanel()
    expect(screen.getByTestId("locations-tree-skeleton")).toBeInTheDocument()
    unmount()

    const refetch = vi.fn()
    hooks.tree.mockReturnValue({ data: undefined, isLoading: false, isError: true, refetch })
    const user = userEvent.setup()
    const error = renderPanel()
    await user.click(screen.getByRole("button", { name: "Retry" }))
    expect(refetch).toHaveBeenCalled()
    error.unmount()

    hooks.tree.mockReturnValue({ data: [], isLoading: false, isError: false, refetch: vi.fn() })
    hooks.flat.mockReturnValue({ data: [], isLoading: false })
    renderPanel()
    expect(screen.getByText("No locations yet")).toBeInTheDocument()
  })
})

describe("LocationsPanel read-only viewer (Phase 30)", () => {
  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("renders the tree read-only without any edit entry", async () => {
    useAuthStore.setState({ accessToken: "jwt", user: { id: "viewer-1", is_read_only: true } as never })
    const user = userEvent.setup()
    renderPanel()

    expect(screen.getByText("1F")).toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: "Add top-level location" }),
    ).not.toBeInTheDocument()
    expect(screen.queryByLabelText("New location name")).not.toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: "More actions for 1F" }),
    ).not.toBeInTheDocument()
    expect(screen.getByTestId("location-node-1")).toHaveAttribute("draggable", "false")
    expect(screen.queryByText(/Tip: drag a node/)).not.toBeInTheDocument()

    // 展開為讀取操作，維持可用
    await user.click(
      within(screen.getByTestId("location-node-1")).getByRole("button", { name: "Expand" }),
    )
    expect(screen.getByText("Kitchen")).toBeInTheDocument()

    // F2 不進入改名
    fireEvent.focus(screen.getByTestId("location-node-1"))
    fireEvent.keyDown(screen.getByTestId("location-node-1"), { key: "F2" })
    expect(screen.queryByLabelText("Rename")).not.toBeInTheDocument()
  })

  it("keeps all edit entries for writers (zero regression)", async () => {
    useAuthStore.setState({ accessToken: "jwt", user: { id: "writer-1", is_read_only: false } as never })
    const user = userEvent.setup()
    renderPanel()

    expect(
      screen.getByRole("button", { name: "Add top-level location" }),
    ).toBeInTheDocument()
    await user.click(
      within(screen.getByTestId("location-node-1")).getByRole("button", {
        name: "More actions for 1F",
      }),
    )
    expect(await screen.findByText("Add child")).toBeInTheDocument()
  })
})

describe("平面圖入口", () => {
  beforeEach(() => { stubHooks() })
  it("更多操作提供平面圖連結", async () => {
    renderPanel()
    await userEvent.setup().click(screen.getByRole("button", { name: "More actions for 1F" }))
    expect(await screen.findByRole("menuitem", { name: "Floor plan" })).toHaveAttribute("href", "/locations/1/plan")
  })
  it("有圖的列提供有 aria-label 的直接入口", () => {
    hooks.tree.mockReturnValue({ data: [{ ...treeData[0], floor_plan_image_id: "image" }], isLoading: false, isError: false })
    renderPanel()
    expect(screen.getByRole("link", { name: "Floor plan for 1F" })).toHaveAttribute("href", "/locations/1/plan")
  })
})
