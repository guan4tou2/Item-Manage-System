import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import type { LocationValueBucket } from "@/lib/api/stats"
import enMessages from "@/messages/en.json"

import {
  ValueLocationChart,
  toLocationValueData,
  truncateLabel,
} from "./value-location-chart"

describe("truncateLabel", () => {
  it("keeps short labels and truncates long ones with an ellipsis", () => {
    expect(truncateLabel("1F / Kitchen")).toBe("1F / Kitchen")
    expect(truncateLabel("a".repeat(24))).toBe("a".repeat(24))
    expect(truncateLabel("a".repeat(30))).toBe("a".repeat(23) + "…")
  })
})

describe("toLocationValueData", () => {
  it("drops zero buckets and keeps both the full path and the axis label", () => {
    const long = "Warehouse A / Rack 12 / Shelf 3 / Bin 45"
    const buckets = [
      { location_id: 1, label: long, value: "2.50", count: 1 },
      { location_id: 2, label: "Shelf", value: "0.00", count: 3 },
    ] satisfies LocationValueBucket[]

    expect(toLocationValueData(buckets, "Unplaced")).toEqual([
      { name: truncateLabel(long), full: long, value: 2.5 },
    ])
  })

  it("uses the unplaced label for items without a location", () => {
    const buckets = [
      { location_id: null, label: null, value: "5.00", count: 1 },
    ] satisfies LocationValueBucket[]

    expect(toLocationValueData(buckets, "Unplaced")).toEqual([
      { name: "Unplaced", full: "Unplaced", value: 5 },
    ])
  })
})

describe("ValueLocationChart", () => {
  it("renders the title and an empty state when every bucket is zero", () => {
    const buckets = [
      { location_id: 1, label: "Shelf", value: "0.00", count: 2 },
    ] satisfies LocationValueBucket[]

    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <ValueLocationChart buckets={buckets} currency="TWD" />
      </NextIntlClientProvider>,
    )

    expect(screen.getByText(enMessages.stats.value.byLocation)).toBeInTheDocument()
    expect(screen.getByText(enMessages.stats.empty.title)).toBeInTheDocument()
  })

  it("stays in loading state (no empty state) while data is pending", () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <ValueLocationChart buckets={[]} currency="TWD" loading />
      </NextIntlClientProvider>,
    )

    expect(screen.queryByText(enMessages.stats.empty.title)).not.toBeInTheDocument()
  })
})
