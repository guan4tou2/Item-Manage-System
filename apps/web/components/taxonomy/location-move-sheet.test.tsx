import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeAll, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import { flattenTree, type TreeFlatNode } from "@/lib/locations/tree"
import type { LocationTreeNode } from "@/lib/api/locations"

import { LocationMoveSheet } from "./location-move-sheet"

vi.mock("@/lib/hooks/use-locations", () => ({ useLocations: () => ({ data: [] }) }))

function node(
  id: number,
  name: string,
  parentId: number | null,
  children: LocationTreeNode[] = [],
): LocationTreeNode {
  return {
    id,
    parent_id: parentId,
    name,
    kind: null,
    sort_order: 0,
    floor_plan_image_id: null,
    path: "",
    item_count: 0,
    children,
  } as LocationTreeNode
}

const flat: TreeFlatNode[] = flattenTree([
  node(1, "1F", null, [node(2, "Kitchen", 1, [node(4, "Top shelf", 2)]), node(3, "Living room", 1)]),
  node(5, "2F", null),
])
const withPaths = flat.map((item) => ({
  ...item,
  path:
    item.id === 4
      ? "1F / Kitchen / Top shelf"
      : item.id === 2
        ? "1F / Kitchen"
        : item.id === 1
          ? "1F"
          : item.id === 3
            ? "1F / Living room"
            : "2F",
}))

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.hasPointerCapture = vi.fn()
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
})

describe("LocationMoveSheet（行動版搬移）", () => {
  it("searches targets by full path and disables invalid ones", async () => {
    const user = userEvent.setup()
    render(
      <LocationMoveSheet
        open
        onOpenChange={vi.fn()}
        node={withPaths.find((item) => item.id === 2)!}
        flat={withPaths}
        onConfirm={vi.fn()}
      />,
      { wrapper: Provider },
    )

    // 自身與其子孫不可選
    expect(
      await screen.findByRole("button", { name: /1F \/ Kitchen \/ Top shelf/ }),
    ).toBeDisabled()
    expect(screen.getByRole("button", { name: /1F \/ Kitchen/ })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Move to top level" })).toBeEnabled()

    await user.type(screen.getByLabelText("Search target location"), "2F")
    expect(screen.queryByRole("button", { name: /1F \/ Living room/ })).toBeNull()
    expect(screen.getByRole("button", { name: /2F/ })).toBeEnabled()
  })

  it("confirms with the chosen target and with root", async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <LocationMoveSheet
        open
        onOpenChange={vi.fn()}
        node={withPaths.find((item) => item.id === 4)!}
        flat={withPaths}
        onConfirm={onConfirm}
      />,
      { wrapper: Provider },
    )

    await user.click(await screen.findByRole("button", { name: /2F/ }))
    expect(onConfirm).toHaveBeenCalledWith(5)

    await user.click(screen.getByRole("button", { name: "Move to top level" }))
    expect(onConfirm).toHaveBeenCalledWith(null)
  })

  it("renders nothing without a node", () => {
    const { container } = render(
      <LocationMoveSheet open onOpenChange={vi.fn()} node={null} flat={withPaths} onConfirm={vi.fn()} />,
      { wrapper: Provider },
    )
    expect(container).toBeEmptyDOMElement()
  })
})
