import { describe, expect, it } from "vitest"

import { extractLocationIdFromPayload } from "@/lib/scan/location-link"

describe("extractLocationIdFromPayload", () => {
  it("取出 items 清單深連結的位置 id", () => {
    expect(extractLocationIdFromPayload("http://localhost/items?location=8")).toBe("8")
  })

  it("忽略其他 query 參數", () => {
    expect(
      extractLocationIdFromPayload("http://localhost/items?location=8&sort=name_asc"),
    ).toBe("8")
  })

  it("非數字的位置參數 → null", () => {
    expect(extractLocationIdFromPayload("http://localhost/items?location=abc")).toBeNull()
  })

  it("缺少 location 參數 → null", () => {
    expect(extractLocationIdFromPayload("http://localhost/items?q=藥")).toBeNull()
  })

  it("物品深連結（/items/{uuid}）→ null（不得誤判）", () => {
    expect(
      extractLocationIdFromPayload(
        "http://localhost/items/08ccb712-4afc-4a80-a8c6-f492166a6ae5",
      ),
    ).toBeNull()
  })

  it("非 URL → null", () => {
    expect(extractLocationIdFromPayload("不是網址")).toBeNull()
    expect(extractLocationIdFromPayload("")).toBeNull()
  })

  it("負數／零 → null（位置 id 為正整數）", () => {
    expect(extractLocationIdFromPayload("http://localhost/items?location=-1")).toBeNull()
    expect(extractLocationIdFromPayload("http://localhost/items?location=0")).toBeNull()
  })
})
