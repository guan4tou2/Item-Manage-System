/**
 * 多格式掃描引擎：原生 `BarcodeDetector`（可用時走快路徑）→
 * `@zxing/browser`（QR ＋ 1D：EAN/UPC/Code128/Code39/ITF）fallback。
 *
 * 單一介面 `createBarcodeEngine(video, onDecode) -> { stop() }`，
 * 相機取得（getUserMedia）由引擎負責；權限錯誤會向外拋。
 */

export interface BarcodeEngine {
  stop(): void
}

export interface EngineOptions {
  /** 測試注入：強制跳过原生偵測器。 */
  native?: boolean
  /** 原生輪詢間隔（毫秒）。 */
  intervalMs?: number
}

export interface NativeBarcodeDetectorCtor {
  new (init?: { formats?: string[] }): {
    detect(source: unknown): Promise<Array<{ rawValue?: string }>>
  }
  getSupportedFormats?: () => Promise<string[]>
}

const NATIVE_FORMATS = [
  "qr_code",
  "ean_13",
  "ean_8",
  "upc_a",
  "upc_e",
  "code_128",
  "code_39",
  "itf",
]

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export async function createBarcodeEngine(
  video: HTMLVideoElement,
  onDecode: (text: string) => void,
  options: EngineOptions = {},
): Promise<BarcodeEngine> {
  const detectorCtor = (
    globalThis as { BarcodeDetector?: NativeBarcodeDetectorCtor }
  ).BarcodeDetector
  if (detectorCtor && options.native !== false) {
    const native = await tryCreateNativeEngine(detectorCtor, video, onDecode, options)
    if (native) return native
  }
  return createZxingEngine(video, onDecode)
}

async function tryCreateNativeEngine(
  ctor: NativeBarcodeDetectorCtor,
  video: HTMLVideoElement,
  onDecode: (text: string) => void,
  options: EngineOptions,
): Promise<BarcodeEngine | null> {
  let formats = [...NATIVE_FORMATS]
  if (typeof ctor.getSupportedFormats === "function") {
    const supported = await ctor.getSupportedFormats()
    formats = NATIVE_FORMATS.filter((format) => supported.includes(format))
    if (formats.length === 0) return null // 原生不支援任何目標格式 → ZXing
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "environment" },
  })
  video.srcObject = stream
  try {
    await video.play()
  } catch {
    // 部分環境（jsdom／尚未有使用者手勢）play 會 reject：非致命，續掃。
  }

  const detector = new ctor({ formats })
  const interval = options.intervalMs ?? 250
  let stopped = false

  const loop = async () => {
    while (!stopped) {
      await sleep(interval)
      if (stopped) break
      try {
        const results = await detector.detect(video)
        const value = results.find((result) => result.rawValue)?.rawValue
        if (value) {
          stopped = true
          onDecode(value)
          break
        }
      } catch {
        // 影格尚未就緒：忽略本輪
      }
    }
  }
  void loop()

  return {
    stop() {
      stopped = true
      const current = video.srcObject as MediaStream | null
      current?.getTracks?.().forEach((track) => track.stop())
      video.srcObject = null
    },
  }
}

async function createZxingEngine(
  video: HTMLVideoElement,
  onDecode: (text: string) => void,
): Promise<BarcodeEngine> {
  // 動態載入：不進首次繪製 bundle（比照既有 QR 掃描作法）
  const [browser, library] = await Promise.all([
    import("@zxing/browser"),
    import("@zxing/library"),
  ])
  const { BrowserMultiFormatReader } = browser
  const { BarcodeFormat, DecodeHintType } = library

  const hints = new Map<number, unknown>()
  hints.set(DecodeHintType.POSSIBLE_FORMATS, [
    BarcodeFormat.QR_CODE,
    BarcodeFormat.EAN_13,
    BarcodeFormat.EAN_8,
    BarcodeFormat.UPC_A,
    BarcodeFormat.UPC_E,
    BarcodeFormat.CODE_128,
    BarcodeFormat.CODE_39,
    BarcodeFormat.ITF,
  ])
  hints.set(DecodeHintType.TRY_HARDER, true)

  const reader = new BrowserMultiFormatReader(hints as never)
  const controls = await reader.decodeFromConstraints(
    { video: { facingMode: "environment" } },
    video,
    (result) => {
      const text = result?.getText()
      if (text) onDecode(text)
    },
  )

  let stopped = false
  return {
    stop() {
      if (stopped) return
      stopped = true
      controls.stop()
    },
  }
}
