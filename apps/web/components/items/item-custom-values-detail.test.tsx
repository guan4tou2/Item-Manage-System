import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import enMessages from "@/messages/en.json"

import { ItemCustomValuesDetail } from "./item-custom-values-detail"

const customFields = [
  { id: 1, name: "Serial number", field_type: "text", created_at: "2026-06-19T00:00:00Z" },
  { id: 2, name: "Fragile", field_type: "bool", created_at: "2026-06-19T00:00:00Z" },
  { id: 3, name: "Purchase date", field_type: "date", created_at: "2026-06-19T00:00:00Z" },
] as const

function renderDetail(values: Array<{ custom_field_id: number; value: string | number | boolean | null }>) {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <ItemCustomValuesDetail customFields={[...customFields]} values={values} />
    </NextIntlClientProvider>,
  )
}

describe("ItemCustomValuesDetail", () => {
  it("formats saved custom values", () => {
    renderDetail([
      { custom_field_id: 1, value: "SN-123" },
      { custom_field_id: 2, value: false },
      { custom_field_id: 3, value: "2026-06-19" },
    ])

    expect(screen.getByText("Custom fields")).toBeInTheDocument()
    expect(screen.getByText("Serial number")).toBeInTheDocument()
    expect(screen.getByText("SN-123")).toBeInTheDocument()
    expect(screen.getByText("Fragile")).toBeInTheDocument()
    expect(screen.getByText("No")).toBeInTheDocument()
    expect(screen.getByText("Purchase date")).toBeInTheDocument()
    expect(screen.getByText("2026-06-19")).toBeInTheDocument()
  })

  it("shows an empty state when fields exist without saved values", () => {
    renderDetail([])

    expect(screen.getByText("Custom fields")).toBeInTheDocument()
    expect(screen.getByText("No custom values yet.")).toBeInTheDocument()
  })
})
