import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeAll, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import type { TreeFlatNode } from "@/lib/locations/tree"

import { LocationDeleteDialog } from "./location-delete-dialog"

vi.mock("@/lib/hooks/use-locations", () => ({
  useLocations: () => ({
    data: [
      { id: 1, parent_id: null, name: "1F", kind: "floor", sort_order: 0, path: "1F" },
      { id: 9, parent_id: null, name: "Roof", kind: null, sort_order: 1, path: "Roof" },
    ],
    isLoading: false,
  }),
}))

const node: TreeFlatNode = {
  id: 2,
  parent_id: 1,
  name: "Kitchen",
  kind: "room",
  sort_order: 0,
  path: "1F / Kitchen",
  item_count: 3,
}

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

function renderDialog(overrides: Partial<React.ComponentProps<typeof LocationDeleteDialog>> = {}) {
  const props = {
    open: true,
    onOpenChange: vi.fn(),
    node,
    itemCount: 3,
    childCount: 0,
    onDelete: vi.fn(),
    ...overrides,
  }
  return render(<LocationDeleteDialog {...props} />, { wrapper: Provider })
}

describe("LocationDeleteDialog（刪除限制）", () => {
  it("shows item and child counts and blocks confirmation", () => {
    renderDialog({ childCount: 2 })

    expect(screen.getByText(/This location holds 3 item\(s\)/)).toBeInTheDocument()
    expect(screen.getByText(/It has 2 child node\(s\)/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled()
  })

  it("allows confirming a clean node", async () => {
    const user = userEvent.setup()
    const onDelete = vi.fn()
    renderDialog({ itemCount: 0, childCount: 0, onDelete })

    const confirm = screen.getByRole("button", { name: "Delete" })
    expect(confirm).toBeEnabled()
    await user.click(confirm)
    expect(onDelete).toHaveBeenCalled()
  })

  it("moves all items to the chosen target", async () => {
    const user = userEvent.setup()
    const onMoveItems = vi.fn()
    renderDialog({ onMoveItems })

    await user.click(screen.getByLabelText("Move target 1"))
    await user.click(await screen.findByRole("option", { name: "Roof" }))
    await user.click(screen.getByRole("button", { name: "Move 3 item(s)" }))

    expect(onMoveItems).toHaveBeenCalledWith(9)
  })

  it("offers handling child nodes first", async () => {
    const user = userEvent.setup()
    const onFocusFirstChild = vi.fn()
    renderDialog({ childCount: 2, onFocusFirstChild })

    await user.click(screen.getByRole("button", { name: "Handle child nodes first" }))
    expect(onFocusFirstChild).toHaveBeenCalled()
  })
})
