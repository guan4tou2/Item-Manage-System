import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { extractItemIdFromPayload, QrScannerView } from "./qr-scanner-view"

const VALID_UUID = "a1b2c3d4-e5f6-4a7b-8c9d-0123456789ab"
const BARCODE = "4710085200016"

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

const lookupMocks = vi.hoisted(() => ({ use: vi.fn(), refetch: vi.fn() }))
vi.mock("@/lib/hooks/use-barcode-lookup", () => ({
  useBarcodeLookup: (code: string | null) => lookupMocks.use(code),
}))

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

function idleLookup() {
  return { data: undefined, isFetching: false, isError: false, refetch: lookupMocks.refetch }
}

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
    lookupMocks.use.mockReset()
    lookupMocks.use.mockReturnValue(idleLookup())
    lookupMocks.refetch.mockReset()
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
    expect(lookupMocks.use).toHaveBeenLastCalledWith(null)
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
      screen.getByRole("button", { name: "Grant permission" }),
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

describe("QrScannerView（位置深連結：Phase 36）", () => {
  beforeEach(() => {
    push.mockReset()
    engineMocks.create.mockReset()
    engineMocks.stop.mockReset()
    engineMocks.create.mockResolvedValue({ stop: engineMocks.stop })
    lookupMocks.use.mockReset()
    lookupMocks.use.mockReturnValue(idleLookup())
    lookupMocks.refetch.mockReset()
    installMediaDevices()
  })

  afterEach(() => {
    removeMediaDevices()
  })

  it("scans a location label and navigates to that location's item list", async () => {
    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()

    act(() => onDecode("https://ims.example/items?location=8"))

    await waitFor(() => expect(push).toHaveBeenCalledWith("/items?location=8"))
    expect(engineMocks.stop).toHaveBeenCalled()
    expect(lookupMocks.use).toHaveBeenLastCalledWith(null)
  })

  it("manual input of a location deep link navigates to the location's item list", async () => {
    render(<QrScannerView />, { wrapper: Provider })

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "https://ims.example/items?location=8" },
    })
    fireEvent.submit(screen.getByRole("textbox").closest("form") as HTMLFormElement)

    expect(push).toHaveBeenCalledWith("/items?location=8")
  })

  it("item deep links still navigate to the item page", async () => {
    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()

    act(() => onDecode(`https://ims.example/items/${VALID_UUID}`))

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(`/items/${VALID_UUID}`),
    )
  })
})

describe("QrScannerView（條碼內查／外查分流）", () => {
  beforeEach(() => {
    push.mockReset()
    engineMocks.create.mockReset()
    engineMocks.stop.mockReset()
    engineMocks.create.mockResolvedValue({ stop: engineMocks.stop })
    lookupMocks.use.mockReset()
    lookupMocks.use.mockReturnValue(idleLookup())
    lookupMocks.refetch.mockReset()
    installMediaDevices()
  })

  afterEach(() => {
    removeMediaDevices()
  })

  it("scanned barcode starts a lookup with the canonical code and stops the camera", async () => {
    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()

    act(() => onDecode(` ${BARCODE.slice(0, 3)}-${BARCODE.slice(3)} `))

    await waitFor(() =>
      expect(lookupMocks.use).toHaveBeenLastCalledWith(BARCODE),
    )
    expect(engineMocks.stop).toHaveBeenCalled()
    expect(push).not.toHaveBeenCalled()
  })

  it("manual barcode input runs a lookup instead of name search", async () => {
    render(<QrScannerView />, { wrapper: Provider })

    fireEvent.change(screen.getByRole("textbox"), { target: { value: BARCODE } })
    fireEvent.submit(screen.getByRole("textbox").closest("form") as HTMLFormElement)

    await waitFor(() =>
      expect(lookupMocks.use).toHaveBeenLastCalledWith(BARCODE),
    )
    expect(push).not.toHaveBeenCalled()
  })

  it("navigates directly when the barcode matches exactly one item", async () => {
    lookupMocks.use.mockReturnValue({
      ...idleLookup(),
      data: {
        code: BARCODE,
        local_matches: [
          { id: "item-1", name: "Milk", quantity: 1, image_id: null, location_path: null },
        ],
        external: null,
        external_status: "skipped",
        cached: false,
      },
    })

    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()
    act(() => onDecode(BARCODE))

    await waitFor(() => expect(push).toHaveBeenCalledWith("/items/item-1"))
  })

  it("renders the candidate list when several items share the barcode", async () => {
    lookupMocks.use.mockReturnValue({
      ...idleLookup(),
      data: {
        code: BARCODE,
        local_matches: [
          { id: "item-1", name: "Milk", quantity: 2, image_id: null, location_path: "1F / Kitchen" },
          { id: "item-2", name: "Milk (spare)", quantity: 1, image_id: null, location_path: null },
        ],
        external: null,
        external_status: "skipped",
        cached: false,
      },
    })

    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()
    act(() => onDecode(BARCODE))

    expect(await screen.findByTestId("barcode-candidates")).toBeInTheDocument()
    expect(screen.getByText("2 matching items")).toBeInTheDocument()
    expect(push).not.toHaveBeenCalled()
  })

  it("renders the external card when nothing matches locally", async () => {
    lookupMocks.use.mockReturnValue({
      ...idleLookup(),
      data: {
        code: BARCODE,
        local_matches: [],
        external: null,
        external_status: "not_found",
        cached: false,
      },
    })

    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()
    act(() => onDecode(BARCODE))

    expect(await screen.findByTestId("barcode-external-card")).toBeInTheDocument()
    expect(
      screen.getByText(/No public data found — barcode carried over/),
    ).toBeInTheDocument()
  })

  it("shows the lookup loading state while querying", async () => {
    lookupMocks.use.mockReturnValue({ ...idleLookup(), isFetching: true })

    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()
    act(() => onDecode(BARCODE))

    expect(await screen.findByTestId("barcode-lookup-loading")).toHaveTextContent(
      "Looking up external database…",
    )
  })

  it("offers retry when the lookup request fails", async () => {
    lookupMocks.use.mockReturnValue({ ...idleLookup(), isError: true })

    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()
    act(() => onDecode(BARCODE))

    const retry = await screen.findByRole("button", { name: "Retry" })
    fireEvent.click(retry)
    expect(lookupMocks.refetch).toHaveBeenCalledTimes(1)
  })

  it("shows a barcode-detected note instead of the not-found note", async () => {
    render(<QrScannerView />, { wrapper: Provider })
    const onDecode = await onDecodeCallback()

    act(() => onDecode(BARCODE))

    expect(await screen.findByText(`✓ Barcode detected: ${BARCODE}`)).toBeInTheDocument()
    expect(screen.queryByText(/Could not identify an item ID/)).toBeNull()
  })
})
