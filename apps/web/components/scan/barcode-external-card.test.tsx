import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"
import type { BarcodeLookup } from "@/lib/api/barcodes"

import { BarcodeExternalCard } from "./barcode-external-card"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

function result(overrides: Partial<BarcodeLookup>): BarcodeLookup {
  return {
    code: "4710085200016",
    local_matches: [],
    external: null,
    external_status: "not_found",
    cached: false,
    ...overrides,
  }
}

describe("BarcodeExternalCard", () => {
  it("shows the source label, name, description, and bring-to-new link on hit", () => {
    render(
      <BarcodeExternalCard
        result={result({
          external_status: "ok",
          external: {
            source: "openfoodfacts",
            name: "Fresh milk",
            description: "Brand, Dairy, 936ml",
            image_url: "https://img.example/milk.jpg",
            suggested_category_id: null,
          },
        })}
        onRetry={vi.fn()}
      />,
      { wrapper: Provider },
    )

    expect(screen.getByTestId("barcode-external-source")).toHaveTextContent(
      "Source: Open Food Facts",
    )
    expect(screen.getByText("Fresh milk")).toBeInTheDocument()
    expect(screen.getByText("Brand, Dairy, 936ml")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Use in new item" })).toHaveAttribute(
      "href",
      "/items/new?barcode=4710085200016",
    )
  })

  it("labels Open Library hits", () => {
    render(
      <BarcodeExternalCard
        result={result({
          external_status: "ok",
          external: {
            source: "openlibrary",
            name: "Clean Code",
            description: "",
            image_url: null,
            suggested_category_id: null,
          },
        })}
        onRetry={vi.fn()}
      />,
      { wrapper: Provider },
    )

    expect(screen.getByTestId("barcode-external-source")).toHaveTextContent(
      "Source: Open Library",
    )
  })

  it("shows the not-found copy and barcode-only creation", () => {
    render(<BarcodeExternalCard result={result({})} onRetry={vi.fn()} />, {
      wrapper: Provider,
    })

    expect(
      screen.getByText(/No public data found — barcode carried over/),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Create with barcode" })).toHaveAttribute(
      "href",
      "/items/new?barcode=4710085200016",
    )
  })

  it("distinguishes network failure from not-found and offers retry", () => {
    const onRetry = vi.fn()
    render(
      <BarcodeExternalCard
        result={result({ external_status: "unavailable" })}
        onRetry={onRetry}
      />,
      { wrapper: Provider },
    )

    expect(screen.getByText("Network unstable — barcode kept.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Retry" }))
    expect(onRetry).toHaveBeenCalledTimes(1)
    expect(screen.getByRole("link", { name: "Create anyway" })).toHaveAttribute(
      "href",
      "/items/new?barcode=4710085200016",
    )
  })

  it("falls back to barcode-only creation for unsupported codes", () => {
    render(
      <BarcodeExternalCard
        result={result({ external_status: "unsupported" })}
        onRetry={vi.fn()}
      />,
      { wrapper: Provider },
    )

    expect(
      screen.getByText("No public database for this barcode type."),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Create with barcode" })).toBeInTheDocument()
  })
})

describe("BarcodeExternalCard read-only viewer (Phase 30)", () => {
  const hit = () =>
    result({
      external_status: "ok",
      external: {
        source: "openfoodfacts",
        name: "Fresh milk",
        description: "Brand, Dairy, 936ml",
        image_url: null,
        suggested_category_id: null,
      },
    })

  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("keeps external info but hides the create entry for viewers", () => {
    useAuthStore.setState({ accessToken: "jwt", user: { id: "viewer-1", is_read_only: true } as never })
    render(<BarcodeExternalCard result={hit()} onRetry={vi.fn()} />, { wrapper: Provider })
    expect(screen.getByText("Fresh milk")).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Use in new item" })).not.toBeInTheDocument()
  })

  it("keeps the create entry for writers (zero regression)", () => {
    useAuthStore.setState({ accessToken: "jwt", user: { id: "writer-1", is_read_only: false } as never })
    render(<BarcodeExternalCard result={hit()} onRetry={vi.fn()} />, { wrapper: Provider })
    expect(screen.getByRole("link", { name: "Use in new item" })).toBeInTheDocument()
  })
})
