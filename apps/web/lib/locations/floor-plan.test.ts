import { describe, expect, it } from "vitest"
import { dragRegion, adjustRegion, toPixels, toNormalized } from "./floor-plan"

describe("平面圖座標", () => {
  it("像素與正規化互轉", () => {
    const region = { x: 0.1, y: 0.2, w: 0.3, h: 0.4 }
    expect(toPixels(region, 200, 100)).toEqual({ x: 20, y: 20, w: 60, h: 40 })
    expect(toNormalized({ x: 20, y: 20, w: 60, h: 40 }, 200, 100)).toEqual(region)
  })
  it("反向拖曳、邊界夾限與最小尺寸", () => {
    expect(dragRegion({ x: 1.2, y: 0.8 }, { x: -0.2, y: 0.2 })).toEqual({
      x: 0,
      y: 0.2,
      w: 1,
      h: 0.6,
    })
    expect(dragRegion({ x: 1, y: 1 }, { x: 1, y: 1 })).toEqual({
      x: 0.98,
      y: 0.98,
      w: 0.02,
      h: 0.02,
    })
  })
  it("鍵盤每次移動或縮放 1%，不越界且可刪除", () => {
    const r = { x: 0, y: 0, w: 0.02, h: 0.02 }
    expect(adjustRegion(r, "ArrowRight", false)).toEqual({ ...r, x: 0.01 })
    expect(adjustRegion(r, "ArrowLeft", false)).toEqual(r)
    expect(adjustRegion(r, "ArrowRight", true)).toEqual({ ...r, w: 0.03 })
    expect(adjustRegion(r, "ArrowUp", true)).toEqual(r)
    expect(adjustRegion(r, "Delete", false)).toBeNull()
    expect(adjustRegion(r, "Backspace", false)).toBeNull()
  })
})
