import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { createBarcodeEngine } from "./barcode-engine"

const zxingMocks = vi.hoisted(() => ({
  stop: vi.fn(),
  decodeFromConstraints: vi.fn(),
  readerHints: [] as unknown[],
  readerCtor: vi.fn(),
}))

vi.mock("@zxing/browser", () => ({
  BrowserMultiFormatReader: class {
    constructor(hints?: unknown) {
      zxingMocks.readerCtor(hints)
    }
    decodeFromConstraints(...args: unknown[]) {
      return zxingMocks.decodeFromConstraints(...args)
    }
  },
}))

vi.mock("@zxing/library", () => ({
  BarcodeFormat: {
    QR_CODE: "qr_code",
    EAN_13: "ean_13",
    EAN_8: "ean_8",
    UPC_A: "upc_a",
    UPC_E: "upc_e",
    CODE_128: "code_128",
    CODE_39: "code_39",
    ITF: "itf",
  },
  DecodeHintType: { POSSIBLE_FORMATS: "formats", TRY_HARDER: "tryHarder" },
}))

interface TrackStub {
  stop: ReturnType<typeof vi.fn>
}

function makeVideo() {
  const video = document.createElement("video")
  Object.defineProperty(video, "play", {
    value: vi.fn().mockResolvedValue(undefined),
    writable: true,
  })
  return video
}

function makeStream(): { stream: MediaStream; tracks: TrackStub[] } {
  const tracks: TrackStub[] = [{ stop: vi.fn() }]
  const stream = { getTracks: () => tracks } as unknown as MediaStream
  return { stream, tracks }
}

function installGetUserMedia(stream: MediaStream) {
  Object.defineProperty(navigator, "mediaDevices", {
    value: { getUserMedia: vi.fn().mockResolvedValue(stream) },
    configurable: true,
    writable: true,
  })
}

function installNativeDetector(
  detect: (video: unknown) => Promise<Array<{ rawValue?: string }>>,
  formats: string[] = ["qr_code", "ean_13", "ean_8", "upc_a", "upc_e", "code_128", "code_39", "itf"],
) {
  const ctor = vi.fn()
  class MockDetector {
    constructor(init?: { formats?: string[] }) {
      ctor(init)
    }
    detect(source: unknown) {
      return detect(source)
    }
    static getSupportedFormats = vi.fn().mockResolvedValue(formats)
  }
  ;(globalThis as { BarcodeDetector?: unknown }).BarcodeDetector = MockDetector
  return ctor
}

beforeEach(() => {
  vi.useFakeTimers()
  zxingMocks.stop.mockClear()
  zxingMocks.decodeFromConstraints.mockReset()
  zxingMocks.readerCtor.mockClear()
})

afterEach(() => {
  vi.useRealTimers()
  delete (globalThis as { BarcodeDetector?: unknown }).BarcodeDetector
})

describe("createBarcodeEngine — 原生 BarcodeDetector 快路徑", () => {
  it("解出條碼後回呼一次並停止輪詢", async () => {
    const { stream, tracks } = makeStream()
    installGetUserMedia(stream)
    installNativeDetector(async () => [{ rawValue: "4710085200016" }])
    const onDecode = vi.fn()

    const engine = await createBarcodeEngine(makeVideo(), onDecode, { intervalMs: 100 })
    await vi.advanceTimersByTimeAsync(120)

    expect(onDecode).toHaveBeenCalledTimes(1)
    expect(onDecode).toHaveBeenCalledWith("4710085200016")

    await vi.advanceTimersByTimeAsync(500)
    expect(onDecode).toHaveBeenCalledTimes(1) // 已停止，不重複回呼

    engine.stop()
    expect(tracks[0]?.stop).toHaveBeenCalled()
  })

  it("以支援格式交集建構偵測器", async () => {
    const { stream } = makeStream()
    installGetUserMedia(stream)
    const ctor = installNativeDetector(async () => [], ["qr_code", "ean_13"])
    const onDecode = vi.fn()

    await createBarcodeEngine(makeVideo(), onDecode, { intervalMs: 50 })
    expect(ctor).toHaveBeenCalledWith({ formats: ["qr_code", "ean_13"] })
  })

  it("忽略影格錯誤直到解出", async () => {
    const { stream } = makeStream()
    installGetUserMedia(stream)
    let calls = 0
    installNativeDetector(async () => {
      calls += 1
      if (calls < 3) throw new Error("frame not ready")
      return [{ rawValue: "96385074" }]
    })
    const onDecode = vi.fn()

    await createBarcodeEngine(makeVideo(), onDecode, { intervalMs: 100 })
    await vi.advanceTimersByTimeAsync(320)

    expect(onDecode).toHaveBeenCalledWith("96385074")
  })

  it("原生不支援任何目標格式時改用 ZXing", async () => {
    const { stream } = makeStream()
    installGetUserMedia(stream)
    installNativeDetector(async () => [], [])
    zxingMocks.decodeFromConstraints.mockResolvedValue({ stop: zxingMocks.stop })
    const onDecode = vi.fn()

    const engine = await createBarcodeEngine(makeVideo(), onDecode)

    expect(zxingMocks.decodeFromConstraints).toHaveBeenCalledTimes(1)
    engine.stop()
    expect(zxingMocks.stop).toHaveBeenCalled()
  })
})

describe("createBarcodeEngine — ZXing fallback", () => {
  it("以環境鏡頭 constraints 啟動並轉發解碼結果", async () => {
    const { stream } = makeStream()
    installGetUserMedia(stream)
    zxingMocks.decodeFromConstraints.mockImplementation(
      async (_constraints, _video, callback: (result: { getText: () => string }) => void) => {
        callback({ getText: () => "4710085200023" })
        return { stop: zxingMocks.stop }
      },
    )
    const onDecode = vi.fn()
    const video = makeVideo()

    const engine = await createBarcodeEngine(video, onDecode)

    const [constraints, passedVideo] =
      zxingMocks.decodeFromConstraints.mock.calls[0] ?? []
    expect(constraints).toEqual({ video: { facingMode: "environment" } })
    expect(passedVideo).toBe(video)
    expect(onDecode).toHaveBeenCalledWith("4710085200023")

    engine.stop()
    engine.stop() // 冪等
    expect(zxingMocks.stop).toHaveBeenCalledTimes(1)
  })

  it("ZXing hints 含 QR 與 1D 格式", async () => {
    const { stream } = makeStream()
    installGetUserMedia(stream)
    zxingMocks.decodeFromConstraints.mockResolvedValue({ stop: zxingMocks.stop })

    await createBarcodeEngine(makeVideo(), vi.fn(), { native: false })

    const hintsArg = zxingMocks.readerCtor.mock.calls[0]?.[0]
    expect(hintsArg).toBeInstanceOf(Map)
    const hints = hintsArg as Map<unknown, unknown>
    expect(hints.get("formats")).toContain("qr_code")
    expect(hints.get("formats")).toContain("ean_13")
    expect(hints.get("formats")).toContain("code_128")
    expect(hints.get("tryHarder")).toBe(true)
  })
})
