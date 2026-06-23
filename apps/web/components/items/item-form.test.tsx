import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, it, expect, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { ItemForm, itemFormSchema, type ItemFormValues } from "./item-form"

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => null,
}))

describe("itemFormSchema", () => {
  const ok = {
    name: "thing", description: "", category_id: null, location_id: null,
    quantity: 1, notes: "", tag_names: [], custom_values: {},
  }

  it("accepts a valid minimal record", () => {
    expect(itemFormSchema.safeParse(ok).success).toBe(true)
  })

  it("rejects empty name", () => {
    const r = itemFormSchema.safeParse({ ...ok, name: "" })
    expect(r.success).toBe(false)
  })

  it("rejects negative quantity", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: -1 })
    expect(r.success).toBe(false)
  })

  it("rejects non-integer quantity", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: 1.5 })
    expect(r.success).toBe(false)
  })

  it("rejects name over 200 chars with nameMax message", () => {
    const r = itemFormSchema.safeParse({ ...ok, name: "a".repeat(201) })
    expect(r.success).toBe(false)
    if (!r.success) expect(r.error.issues[0]?.message).toBe("nameMax")
  })

  it("reports nameRequired for empty name", () => {
    const r = itemFormSchema.safeParse({ ...ok, name: "" })
    if (!r.success) expect(r.error.issues[0]?.message).toBe("nameRequired")
  })

  it("reports quantityMin for negative", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: -1 })
    if (!r.success) expect(r.error.issues[0]?.message).toBe("quantityMin")
  })

  it("reports quantityInteger for non-integer", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: 1.5 })
    if (!r.success) expect(r.error.issues[0]?.message).toBe("quantityInteger")
  })

  it("accepts numeric string for quantity via coercion", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: "5" as unknown as number })
    expect(r.success).toBe(true)
  })

  it("accepts custom field values", () => {
    const r = itemFormSchema.safeParse({
      ...ok,
      custom_values: {
        "1": "SN-123",
        "2": 12,
        "3": true,
      },
    })
    expect(r.success).toBe(true)
  })
})

function renderItemForm(
  defaultValues: ItemFormValues,
  onSubmit = vi.fn(),
  itemTemplates = [] as Array<{
    id: number
    name: string
    payload: Record<string, unknown>
    created_at: string
  }>,
) {
  return {
    onSubmit,
    ...render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <ItemForm
          defaultValues={defaultValues}
          onSubmit={onSubmit}
          onCancel={() => undefined}
          submitting={false}
          categories={[]}
          locations={[]}
          tagSuggestions={[]}
          itemTemplates={itemTemplates}
          customFields={[
            { id: 1, name: "Serial number", field_type: "text", created_at: "2026-06-19T00:00:00Z" },
            { id: 2, name: "Capacity", field_type: "number", created_at: "2026-06-19T00:00:00Z" },
            { id: 3, name: "Purchase date", field_type: "date", created_at: "2026-06-19T00:00:00Z" },
            { id: 4, name: "Fragile", field_type: "bool", created_at: "2026-06-19T00:00:00Z" },
          ]}
        />
      </NextIntlClientProvider>,
    ),
  }
}

describe("ItemForm custom fields", () => {
  const defaults: ItemFormValues = {
    name: "thing",
    description: "",
    category_id: null,
    location_id: null,
    quantity: 1,
    notes: "",
    image_id: null,
    tag_names: [],
    custom_values: {},
  }

  it("renders configured custom fields", () => {
    renderItemForm(defaults)

    expect(screen.getByText("Custom fields")).toBeInTheDocument()
    expect(screen.getByLabelText("Serial number")).toBeInTheDocument()
    expect(screen.getByLabelText("Capacity")).toBeInTheDocument()
    expect(screen.getByLabelText("Purchase date")).toBeInTheDocument()
    expect(screen.getByRole("checkbox", { name: "Fragile" })).toBeInTheDocument()
  })

  it("submits typed custom values", async () => {
    const { onSubmit } = renderItemForm(defaults)

    fireEvent.change(screen.getByLabelText("Serial number"), {
      target: { value: "SN-123" },
    })
    fireEvent.change(screen.getByLabelText("Capacity"), {
      target: { value: "12" },
    })
    fireEvent.change(screen.getByLabelText("Purchase date"), {
      target: { value: "2026-06-19" },
    })
    fireEvent.click(screen.getByRole("checkbox", { name: "Fragile" }))
    fireEvent.click(screen.getByRole("button", { name: "Save" }))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          custom_values: {
            "1": "SN-123",
            "2": 12,
            "3": "2026-06-19",
            "4": true,
          },
        }),
        expect.anything(),
      )
    })
  })
})

describe("ItemForm templates", () => {
  const defaults: ItemFormValues = {
    name: "",
    description: "",
    category_id: null,
    location_id: null,
    quantity: 1,
    notes: "",
    image_id: null,
    tag_names: [],
    custom_values: {},
  }

  it("applies template payloads to the editable fields", async () => {
    const { onSubmit } = renderItemForm(defaults, vi.fn(), [
      {
        id: 10,
        name: "Restock pack",
        payload: {
          name: "AA Battery",
          quantity: 12,
          notes: "Top shelf",
          custom_values: { "1": "SN-TEMPLATE" },
        },
        created_at: "2026-06-19T00:00:00Z",
      },
    ])

    fireEvent.click(screen.getByRole("button", { name: "Restock pack" }))

    expect(screen.getByLabelText("Name")).toHaveValue("AA Battery")
    expect(screen.getByLabelText("Quantity")).toHaveValue(12)
    expect(screen.getByLabelText("Notes")).toHaveValue("Top shelf")
    expect(screen.getByLabelText("Serial number")).toHaveValue("SN-TEMPLATE")

    fireEvent.click(screen.getByRole("button", { name: "Save" }))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "AA Battery",
          quantity: 12,
          notes: "Top shelf",
          custom_values: expect.objectContaining({
            "1": "SN-TEMPLATE",
          }),
        }),
        expect.anything(),
      )
    })
  })

  it("shows applied template status and clears only unchanged template values", async () => {
    renderItemForm(
      { ...defaults, description: "Keep this description" },
      vi.fn(),
      [
        {
          id: 10,
          name: "Restock pack",
          payload: {
            name: "AA Battery",
            quantity: 12,
            notes: "Top shelf",
            custom_values: { "1": "SN-TEMPLATE" },
          },
          created_at: "2026-06-19T00:00:00Z",
        },
      ],
    )

    expect(screen.getByRole("button", { name: "Clear template values" })).toBeDisabled()

    fireEvent.click(screen.getByRole("button", { name: "Restock pack" }))

    expect(screen.getByText("Applied template: Restock pack")).toBeInTheDocument()
    expect(screen.getByText("4 fields applied: Name, Quantity, Notes, Serial number")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Restock pack" })).toHaveAttribute("aria-pressed", "true")

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Manual override" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Clear template values" }))

    expect(screen.getByLabelText("Name")).toHaveValue("Manual override")
    expect(screen.getByLabelText("Description")).toHaveValue("Keep this description")
    expect(screen.getByLabelText("Quantity")).toHaveValue(1)
    expect(screen.getByLabelText("Notes")).toHaveValue("")
    expect(screen.getByLabelText("Serial number")).toHaveValue("")
  })

  it("keeps focus inside the template controls after apply and clear", async () => {
    renderItemForm(defaults, vi.fn(), [
      {
        id: 10,
        name: "Restock pack with a very long name that should truncate",
        payload: { name: "AA Battery" },
        created_at: "2026-06-19T00:00:00Z",
      },
    ])

    const templateButton = screen.getByRole("button", {
      name: "Restock pack with a very long name that should truncate",
    })
    templateButton.focus()
    fireEvent.click(templateButton)

    expect(templateButton).toHaveFocus()

    fireEvent.click(screen.getByRole("button", { name: "Clear template values" }))

    await waitFor(() => {
      expect(templateButton).toHaveFocus()
    })
  })
})
