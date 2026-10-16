import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { extractItemIdFromPayload, QrScannerView } from "./qr-scanner-view"

const VALID_UUID = "a1b2c3d4-e5f6-4a7b-8c9d-0123456789ab"

const navMocks = vi.hoisted(() => {
  const push = vi.fn()
  return { push, router: { push } }
})
const push = navMocks.push
vi.mock("next/navigation", () => ({ useRouter: () => navMocks.router }))

const engineMocks = vi.hoisted(() => ({ create: vi.fn(), stop: vi.fn() }))
vi.mock("@/lib/scan/barcode-engine", () => ({
  createBarcodeEngine: (...args: unknown[]) => engineMocks.create(...args),
}))

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

function installMediaDevices() {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn() },
  })
}

function removeMediaDevices() {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: undefined,
  })
}

async function onDecodeCallback() {
  await waitFor(() => expect(engineMocks.create).toHaveBeenCalled())
  return engineMocks.create.mock.calls[0]?.[1] as (text: string) => void
}

describe("extractItemIdFromPayload", () => {
  it("extracts UUID from a /items/{id} URL", () => {
    expect(
      extractItemIdFromPayload(`https://example.com/items/${VALID_UUID}`),
    ).toBe(VALID_UUID)
  })

  it("extracts UUID from a nested /items/{id} URL", () => {
    expect(
      extractItemIdFromPayload(
        `https://example.com/locale/en/items/${VALID_UUID}?ref=label`,
      ),
    ).toBe(VALID_UUID)
  })

  it("accepts a bare UUID as payload", () => {
    expect(extractItemIdFromPayload(VALID_UUID)).toBe(VALID_UUID)
  })

  it("lowercases the UUID for consistency", () => {
    const upper = VALID_UUID.toUpperCase()
    expect(extractItemIdFromPayload(upper)).toBe(VALID_UUID)
  })

  it("trims whitespace before parsing", () => {
    expect(extractItemIdFromPayload(`  ${VALID_UUID}  `)).toBe(VALID_UUID)
  })

  it("returns null for a non-items URL", () => {
    expect(
      extractItemIdFromPayload("https://example.com/users/abc"),
    ).toBeNull()
  })

  it("returns null for a URL without a UUID under /items", () => {
    expect(
      extractItemIdFromPayload("https://example.com/items/not-a-uuid"),
    ).toBeNull()
  })

  it("returns null for arbitrary text", () => {
    expect(extractItemIdFromPayload("hello world")).toBeNull()
  })

  it("returns null for an empty payload", () => {
    expect(extractItemIdFromPayload("")).toBeNull()
  })
})

describe("QrScannerView（QR 零回歸＋相機狀態）", () => {
  beforeEach(() => {
    push.mockReset()
    engineMocks.create.mockReset()
    engineMocks.stop.mockReset()
    engineMocks.create.mockResolvedValue({ stop: engineMocks.stop })
    installMediaDevices()
  })

  afterEach(() => {
    removeMediaDevices()
  })

  it("scans a QR deep link and navigates to the item page", async () => {
    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()

    act(() => onDecode(`https://ims.example/items/${VALID_UUID}`))

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(`/items/${VALID_UUID}`),
    )
    expect(engineMocks.stop).toHaveBeenCalled()
  })

  it("scans a bare UUID and navigates", async () => {
    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()

    act(() => onDecode(VALID_UUID))

    await waitFor(() => expect(push).toHaveBeenCalledWith(`/items/${VALID_UUID}`))
  })

  it("manual input of a UUID navigates to the item", async () => {
    render(<QrScannerView />, { wrapper: Provider })

    fireEvent.change(screen.getByRole("textbox"), { target: { value: VALID_UUID } })
    fireEvent.submit(screen.getByRole("textbox").closest("form") as HTMLFormElement)

    expect(push).toHaveBeenCalledWith(`/items/${VALID_UUID}`)
  })

  it("manual input of a keyword falls back to name search", async () => {
    render(<QrScannerView />, { wrapper: Provider })

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "牛奶" } })
    fireEvent.submit(screen.getByRole("textbox").closest("form") as HTMLFormElement)

    expect(push).toHaveBeenCalledWith(`/items?q=${encodeURIComponent("牛奶")}`)
  })

  it("shows the denied state when camera permission is refused", async () => {
    const err = Object.assign(new Error("Permission denied"), {
      name: "NotAllowedError",
    })
    engineMocks.create.mockRejectedValue(err)

    render(<QrScannerView />, { wrapper: Provider })

    expect(await screen.findByText(/Camera permission denied/i)).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Restart camera" }),
    ).toBeInTheDocument()
  })

  it("shows unsupported state when there is no camera API", async () => {
    removeMediaDevices()
    render(<QrScannerView />, { wrapper: Provider })

    expect(await screen.findByText(/No camera found/i)).toBeInTheDocument()
    expect(engineMocks.create).not.toHaveBeenCalled()
  })

  it("restart button retries camera start", async () => {
    const err = Object.assign(new Error("boom"), { name: "NotReadableError" })
    engineMocks.create.mockRejectedValueOnce(err)

    render(<QrScannerView />, { wrapper: Provider })
    const restart = await screen.findByRole("button", { name: "Restart camera" })

    engineMocks.create.mockResolvedValue({ stop: engineMocks.stop })
    fireEvent.click(restart)

    await waitFor(() => expect(engineMocks.create).toHaveBeenCalledTimes(2))
  })
})
