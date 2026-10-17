import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import type { CategoryValueBucket } from "@/lib/api/stats"
import enMessages from "@/messages/en.json"

import { ValueCategoryChart, toCategoryValueData } from "./value-category-chart"

describe("toCategoryValueData", () => {
  it("drops zero-value buckets and maps amounts to numbers", () => {
    const buckets = [
      { category_id: 1, name: "Coffee", value: "10.50", count: 2 },
      { category_id: 2, name: "Tea", value: "0.00", count: 3 },
    ] satisfies CategoryValueBucket[]

    expect(toCategoryValueData(buckets, "Uncategorized")).toEqual([
      { name: "Coffee", value: 10.5, count: 2 },
    ])
  })

  it("labels null categories with the uncategorized text", () => {
    const buckets = [
      { category_id: null, name: null, value: "3.00", count: 1 },
    ] satisfies CategoryValueBucket[]

    expect(toCategoryValueData(buckets, "Uncategorized")).toEqual([
      { name: "Uncategorized", value: 3, count: 1 },
    ])
  })
})

describe("ValueCategoryChart", () => {
  it("renders the title and an empty state when every bucket is zero", () => {
    const buckets = [
      { category_id: 1, name: "Coffee", value: "0.00", count: 2 },
    ] satisfies CategoryValueBucket[]

    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <ValueCategoryChart buckets={buckets} currency="TWD" />
      </NextIntlClientProvider>,
    )

    expect(screen.getByText(enMessages.stats.value.byCategory)).toBeInTheDocument()
    expect(screen.getByText(enMessages.stats.empty.title)).toBeInTheDocument()
  })

  it("stays in loading state (no empty state) while data is pending", () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <ValueCategoryChart buckets={[]} currency="TWD" loading />
      </NextIntlClientProvider>,
    )

    expect(screen.queryByText(enMessages.stats.empty.title)).not.toBeInTheDocument()
  })
})
