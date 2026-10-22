"use client"

import { useEffect, useState } from "react"

interface Props {
  /** 條碼內容（`items.barcode`；使用者自訂字串）。 */
  value: string | null | undefined
}

/**
 * 標籤用 Code128 條碼圖（Phase 37）。
 *
 * - 以 `bwip-js`（MIT）產生 **SVG 字串**（可列印、體積小、不需 canvas 文字量測）
 * - 函式庫需動態載入 → `import()` 於 effect 內（不進首次繪製 bundle；
 *   比照 Phase 25 掃碼引擎的動態載入作法）
 * - **可編碼性自行驗證**：Code128 僅能編碼可列印 ASCII；`bwip-js` 對中文等
 *   非法字元**不會報錯**而是產生內容不符的條碼（掃出來是亂碼）→ 故先擋掉，
 *   退回純文字條碼值（整張標籤仍可列印，不因一筆髒資料壞掉整批）
 * - 條碼**數字**由呼叫端以文字呈現（沿用既有標籤版面），此處只畫條碼本體
 */

/** Code128 可編碼字元：可列印 ASCII（0x20–0x7E）。 */
const CODE128_ENCODABLE = /^[\x20-\x7e]+$/

export function isCode128Encodable(value: string | null | undefined): boolean {
  const text = (value ?? "").trim()
  return text.length > 0 && CODE128_ENCODABLE.test(text)
}

export function LabelBarcode({ value }: Props) {
  const [svg, setSvg] = useState<string | null>(null)

  useEffect(() => {
    const text = (value ?? "").trim()
    if (!isCode128Encodable(text)) {
      setSvg(null)
      return
    }
    let active = true
    void import("bwip-js")
      .then(({ default: bwipjs }) => {
        if (!active) return
        try {
          setSvg(
            bwipjs.toSVG({
              bcid: "code128",
              text,
              scale: 2,
              height: 10,
              includetext: false,
              paddingwidth: 0,
              paddingheight: 0,
              backgroundcolor: "FFFFFF",
            }),
          )
        } catch {
          // 無法編碼 → 退回純文字
          setSvg(null)
        }
      })
      .catch(() => {
        if (active) setSvg(null)
      })
    return () => {
      active = false
    }
  }, [value])

  if (!svg) return null

  return (
    <div
      data-testid="label-barcode"
      className="flex w-full justify-center [&>svg]:h-[1.1cm] [&>svg]:w-auto"
      // biome-ignore lint/security/noDangerouslySetInnerHTML: bwip-js 產生的機器生成 SVG（無文字注入）
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}
