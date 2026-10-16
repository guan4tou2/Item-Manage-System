import { render, screen } from "@testing-library/react"
import { useState } from "react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import type { LocationRead } from "@/lib/api/locations"

import { LocationSelect } from "./location-select"

const mobile = vi.hoisted(() => ({ value: false }))
vi.mock("@/lib/hooks/use-is-mobile", () => ({ useIsMobile: () => mobile.value }))
vi.mock("@/lib/hooks/use-locations", () => ({ useLocations: () => ({ data: [] }) }))

const nodes: LocationRead[] = [
  { id: 1, parent_id: null, name: "1F", kind: "floor", sort_order: 0, floor_plan_image_id: null, path: "1F" },
  { id: 2, parent_id: 1, name: "Kitchen", kind: "room", sort_order: 0, floor_plan_image_id: null, path: "1F / Kitchen" },
  { id: 3, parent_id: 2, name: "Top shelf", kind: null, sort_order: 0, floor_plan_image_id: null, path: "1F / Kitchen / Top shelf" },
  { id: 4, parent_id: null, name: "2F", kind: "floor", sort_order: 1, floor_plan_image_id: null, path: "2F" },
]

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

/** 受控包裝（真實使用情境：值由外部持有）。 */
function Controlled({
  initial = null,
  onChange,
  label = "Location",
}: {
  initial?: number | null
  onChange?: (id: number | null) => void
  label?: string
}) {
  const [value, setValue] = useState<number | null>(initial)
  return (
    <LocationSelect
      value={value}
      onChange={(id) => {
        setValue(id)
        onChange?.(id)
      }}
      nodes={nodes}
      label={label}
    />
  )
}

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.hasPointerCapture = vi.fn()
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
})

beforeEach(() => {
  mobile.value = false
})

describe("LocationSelect（桌機 cascading）", () => {
  it("drills through levels and reports the deepest chosen node", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<Controlled onChange={onChange} />, { wrapper: Provider })

    await user.click(screen.getByLabelText("Location 1"))
    await user.click(await screen.findByRole("option", { name: "1F" }))
    expect(onChange).toHaveBeenCalledWith(1)

    // 選了 1F → 出現第二層
    await user.click(screen.getByLabelText("Location 2"))
    await user.click(await screen.findByRole("option", { name: "Kitchen" }))
    expect(onChange).toHaveBeenLastCalledWith(2)

    // 第三層
    await user.click(screen.getByLabelText("Location 3"))
    await user.click(await screen.findByRole("option", { name: "Top shelf" }))
    expect(onChange).toHaveBeenLastCalledWith(3)
  })

  it("restores the cascading levels from an external value and shows the path", () => {
    render(<Controlled initial={3} />, { wrapper: Provider })

    expect(screen.getByLabelText("Location 1")).toBeInTheDocument()
    expect(screen.getByLabelText("Location 2")).toBeInTheDocument()
    expect(screen.getByLabelText("Location 3")).toBeInTheDocument()
    expect(screen.getByTestId("location-select-path")).toHaveTextContent(
      "1F / Kitchen / Top shelf",
    )
  })

  it("shows a drill-down placeholder on deeper levels until chosen", async () => {
    const user = userEvent.setup()
    render(<Controlled />, { wrapper: Provider })

    await user.click(screen.getByLabelText("Location 1"))
    await user.click(await screen.findByRole("option", { name: "1F" }))

    // 第二層出現但尚未選 → 顯示「再往下選…」placeholder（非「(None)」）
    expect(await screen.findByText("Drill down…")).toBeInTheDocument()
  })

  it("clears the selection through the level-1 option when allowed", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<Controlled initial={2} onChange={onChange} />, { wrapper: Provider })

    await user.click(screen.getByLabelText("Location 1"))
    await user.click(await screen.findByRole("option", { name: "(None)" }))
    expect(onChange).toHaveBeenCalledWith(null)
  })
})

describe("LocationSelect（行動版 bottom sheet）", () => {
  beforeEach(() => {
    mobile.value = true
  })

  it("opens a searchable sheet and fills the value on tap", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<Controlled onChange={onChange} />, { wrapper: Provider })

    await user.click(screen.getByRole("button", { name: "Location" }))
    await user.type(screen.getByLabelText("Search locations"), "shelf")
    await user.click(screen.getByRole("button", { name: /1F \/ Kitchen \/ Top shelf/ }))

    expect(onChange).toHaveBeenCalledWith(3)
  })

  it("shows the current path on the trigger", () => {
    render(<Controlled initial={2} />, { wrapper: Provider })

    expect(screen.getByRole("button", { name: "Location" })).toHaveTextContent(
      "1F / Kitchen",
    )
  })
})
