import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, it, expect, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { ItemForm, itemFormSchema, type ItemFormValues } from "./item-form"

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => null,
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const lookupMocks = vi.hoisted(() => ({ use: vi.fn() }))
vi.mock("@/lib/hooks/use-barcode-lookup", () => ({
  useBarcodeLookup: (code: string | null) => lookupMocks.use(code),
}))

function idleLookup() {
  return { data: undefined, isFetching: false, isError: false, refetch: vi.fn() }
}

beforeEach(() => {
  lookupMocks.use.mockReset()
  lookupMocks.use.mockReturnValue(idleLookup())
})

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

  it("accepts a barcode and rejects one over 32 chars", () => {
    expect(itemFormSchema.safeParse({ ...ok, barcode: "4710085200016" }).success).toBe(true)
    const r = itemFormSchema.safeParse({ ...ok, barcode: "9".repeat(33) })
    expect(r.success).toBe(false)
    if (!r.success) expect(r.error.issues[0]?.message).toBe("barcodeMax")
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
  batchOptions: {
    trackBatches?: boolean
    trackBatchesLocked?: boolean
    onTrackBatchesChange?: (value: boolean) => void
  } = {},
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
          trackBatches={batchOptions.trackBatches}
          trackBatchesLocked={batchOptions.trackBatchesLocked}
          onTrackBatchesChange={batchOptions.onTrackBatchesChange}
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

describe("ItemForm batch tracking", () => {
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

  it("shows the quantity input while tracking is off", () => {
    renderItemForm(defaults)

    expect(screen.getByLabelText("Quantity")).toBeInTheDocument()
    expect(screen.getByLabelText("Track batches")).not.toBeChecked()
  })

  it("hides quantity and explains absorption when tracking is on", () => {
    renderItemForm(defaults, vi.fn(), [], { trackBatches: true })

    expect(screen.queryByLabelText("Quantity")).not.toBeInTheDocument()
    expect(
      screen.getByText(
        "The first batch will fold in the existing quantity of 1 with no expiry date.",
      ),
    ).toBeInTheDocument()
  })

  it("locks the switch and points to the item page once tracking is on", () => {
    renderItemForm(defaults, vi.fn(), [], {
      trackBatches: true,
      trackBatchesLocked: true,
    })

    expect(screen.getByLabelText("Track batches")).toBeDisabled()
    expect(
      screen.getByText(
        "Batch tracking is on; disable it from the batch section on the item page.",
      ),
    ).toBeInTheDocument()
  })

  it("reports switch changes to the parent", () => {
    const onChange = vi.fn()
    renderItemForm(defaults, vi.fn(), [], { onTrackBatchesChange: onChange })

    fireEvent.click(screen.getByLabelText("Track batches"))

    expect(onChange).toHaveBeenCalledWith(true)
  })
})

describe("ItemForm barcode", () => {
  const defaults: ItemFormValues = {
    name: "",
    description: "",
    barcode: "",
    category_id: null,
    location_id: null,
    quantity: 1,
    notes: "",
    image_id: null,
    tag_names: [],
    custom_values: {},
  }

  function renderBarcodeForm(
    overrides: Partial<ItemFormValues> = {},
    barcodePrefill: string | null = null,
  ) {
    const onSubmit = vi.fn()
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <ItemForm
          defaultValues={{ ...defaults, ...overrides }}
          onSubmit={onSubmit}
          onCancel={() => undefined}
          submitting={false}
          categories={[]}
          locations={[]}
          tagSuggestions={[]}
          barcodePrefill={barcodePrefill}
        />
      </NextIntlClientProvider>,
    )
    return { onSubmit }
  }

  const externalHit = {
    code: "4710085200016",
    local_matches: [],
    external: {
      source: "openfoodfacts",
      name: "Fresh milk",
      description: "Brand, Dairy, 936ml",
      image_url: null,
      suggested_category_id: 7,
    },
    external_status: "ok",
    cached: false,
  }

  it("renders the barcode field with a lookup button", () => {
    renderBarcodeForm()

    expect(screen.getByLabelText("Barcode")).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Look up external data by barcode" }),
    ).toBeInTheDocument()
  })

  it("looks up the canonicalized barcode typed into the field", async () => {
    renderBarcodeForm()

    fireEvent.change(screen.getByLabelText("Barcode"), {
      target: { value: "978-0-306-40615-7" },
    })
    fireEvent.click(
      screen.getByRole("button", { name: "Look up external data by barcode" }),
    )

    await waitFor(() =>
      expect(lookupMocks.use).toHaveBeenLastCalledWith("9780306406157"),
    )
    expect(screen.getByLabelText("Barcode")).toHaveValue("9780306406157")
  })

  it("rejects a non-barcode value without calling the API", async () => {
    const { toast } = await import("sonner")
    renderBarcodeForm()

    fireEvent.change(screen.getByLabelText("Barcode"), {
      target: { value: "hello" },
    })
    fireEvent.click(
      screen.getByRole("button", { name: "Look up external data by barcode" }),
    )

    expect(toast.error).toHaveBeenCalled()
    expect(lookupMocks.use).not.toHaveBeenCalledWith("hello")
  })

  it("prefills empty name, description, and category from an external hit", async () => {
    lookupMocks.use.mockReturnValue({ ...idleLookup(), data: externalHit })

    renderBarcodeForm({}, "4710085200016")

    await waitFor(() =>
      expect(screen.getByLabelText("Name")).toHaveValue("Fresh milk"),
    )
    expect(screen.getByLabelText("Description")).toHaveValue("Brand, Dairy, 936ml")
    expect(lookupMocks.use).toHaveBeenLastCalledWith("4710085200016")
    expect(screen.getByTestId("barcode-prefill-source")).toHaveTextContent(
      "Name and description filled from Open Food Facts",
    )
  })

  it("never overwrites fields the user already filled", async () => {
    lookupMocks.use.mockReturnValue({ ...idleLookup(), data: externalHit })

    renderBarcodeForm({ name: "My own name" }, "4710085200016")

    await waitFor(() =>
      expect(screen.getByLabelText("Description")).toHaveValue(
        "Brand, Dairy, 936ml",
      ),
    )
    expect(screen.getByLabelText("Name")).toHaveValue("My own name")
  })

  it("shows a notice instead of prefilling when items already share the barcode", async () => {
    lookupMocks.use.mockReturnValue({
      ...idleLookup(),
      data: {
        code: "4710085200016",
        local_matches: [
          { id: "item-1", name: "Milk", quantity: 1, image_id: null, location_path: null },
        ],
        external: null,
        external_status: "skipped",
        cached: false,
      },
    })

    renderBarcodeForm({}, "4710085200016")

    expect(await screen.findByTestId("barcode-local-notice")).toHaveTextContent(
      "1 item(s) already share this barcode.",
    )
    expect(screen.getByLabelText("Name")).toHaveValue("")
    expect(screen.queryByTestId("barcode-prefill-source")).toBeNull()
  })
})
