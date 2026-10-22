import { render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { isCode128Encodable, LabelBarcode } from "./label-barcode"

describe("isCode128Encodable", () => {
  it("接受可列印 ASCII", () => {
    expect(isCode128Encodable("4710085200016")).toBe(true)
    expect(isCode128Encodable("ABC-123")).toBe(true)
  })

  it("拒絕中文／emoji／空值", () => {
    expect(isCode128Encodable("中文條碼")).toBe(false)
    expect(isCode128Encodable("📦")).toBe(false)
    expect(isCode128Encodable("")).toBe(false)
    expect(isCode128Encodable(null)).toBe(false)
  })
})

describe("LabelBarcode", () => {
  it("renders a Code128 barcode SVG for an encodable value", async () => {
    const { container } = render(<LabelBarcode value="4710085200016" />)

    const holder = await screen.findByTestId("label-barcode")
    await waitFor(() => expect(holder.querySelector("svg")).not.toBeNull())
    // 條碼本體（bwip-js 以 path 畫條）
    expect(container.querySelectorAll("path").length).toBeGreaterThan(0)
  })

  it("renders nothing for an empty value", async () => {
    const { container } = render(<LabelBarcode value="" />)
    await waitFor(() => expect(container.querySelector("svg")).toBeNull())
    expect(screen.queryByTestId("label-barcode")).toBeNull()
  })

  it("falls back to no barcode when the value cannot be encoded", async () => {
    // Code128 無法編碼中文 → 不得讓整張標籤失敗（退回純文字）
    const { container } = render(<LabelBarcode value="中文條碼" />)

    await waitFor(() => {
      expect(container.querySelector("svg")).toBeNull()
    })
    expect(screen.queryByTestId("label-barcode")).toBeNull()
  })
})
