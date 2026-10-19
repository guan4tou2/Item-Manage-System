import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeAll, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import zhMessages from "@/messages/zh-TW.json"
import type { CategoryTreeNode } from "@/lib/api/categories"

import { CategorySelect, flattenCategories } from "./category-select"

const categories: CategoryTreeNode[] = [
  {
    id: 3,
    name: "Kitchen",
    parent_id: null,
    children: [
      { id: 4, name: "Mugs", parent_id: 3, children: [] },
      { id: 5, name: "Tools", parent_id: 3, children: [] },
    ],
  },
  { id: 9, name: "Storage", parent_id: null, children: [] },
]

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

describe("flattenCategories", () => {
  it("flattens the tree depth-first with indentation", () => {
    expect(flattenCategories(categories)).toEqual([
      { id: 3, label: "Kitchen" },
      { id: 4, label: "— Mugs" },
      { id: 5, label: "— Tools" },
      { id: 9, label: "Storage" },
    ])
  })

  it("returns an empty list for an empty tree", () => {
    expect(flattenCategories([])).toEqual([])
  })
})

describe("CategorySelect", () => {
  it("reports the chosen category id", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <CategorySelect
        value={null}
        onChange={onChange}
        categories={categories}
        label="Category"
      />,
      { wrapper: Provider },
    )

    await user.click(screen.getByLabelText("Category"))
    await user.click(await screen.findByRole("option", { name: "— Mugs" }))

    expect(onChange).toHaveBeenCalledWith(4)
  })

  it("clears the selection through the none option", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <CategorySelect
        value={3}
        onChange={onChange}
        categories={categories}
        label="Category"
      />,
      { wrapper: Provider },
    )

    await user.click(screen.getByLabelText("Category"))
    await user.click(await screen.findByRole("option", { name: "(None)" }))

    expect(onChange).toHaveBeenCalledWith(null)
  })

  it("shows the localized none label and selected value", () => {
    render(
      <CategorySelect
        value={3}
        onChange={vi.fn()}
        categories={categories}
        label="Category"
        testId="draft-category"
      />,
      { wrapper: Provider },
    )

    const trigger = screen.getByTestId("draft-category")
    expect(trigger).toHaveAttribute("aria-label", "Category")
    expect(trigger).toHaveTextContent("Kitchen")
  })

  it("localizes the none option in zh-TW", async () => {
    const user = userEvent.setup()
    render(
      <NextIntlClientProvider locale="zh-TW" messages={zhMessages}>
        <CategorySelect value={null} onChange={vi.fn()} categories={categories} label="分類" />
      </NextIntlClientProvider>,
    )

    await user.click(screen.getByLabelText("分類"))
    expect(await screen.findByRole("option", { name: "(未分類)" })).toBeInTheDocument()
  })
})
