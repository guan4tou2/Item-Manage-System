import { describe, expect, it } from "vitest"
import { itemValuation } from "./valuation"
import { isValidCost } from "./cost"

const batch = (unit_cost: string | null, quantity = 2, is_depleted = false) => ({ unit_cost, quantity, is_depleted })

describe("D3 物品估值", () => {
  it.each([
    [false, "10", [batch("2")], "40.00"],
    [false, null, [batch("2")], "0.00"],
    [true, "10", [batch("2"), batch("3")], "10.00"],
    [true, "10", [batch("2"), batch(null)], "24.00"],
    [true, "10", [batch(null), batch(null)], "40.00"],
    [true, null, [batch(null), batch(null)], "0.00"],
    [true, null, [batch("2"), batch(null)], "4.00"],
    [true, "10", [batch("0"), batch("99", 5, true)], "0.00"],
    [true, "10", [], "0.00"],
    [true, null, [batch("0.10", 3), batch("0.20", 1)], "0.50"],
    [true, null, [batch("9999999999.99", 1000000)], "9999999999990000.00"],
  ] as const)("批次 %s／預設 %s／組合 %#", (tracked, cost, rows, expected) => {
    expect(itemValuation(tracked, 4, cost, rows)).toBe(expected)
  })
})

describe("共用成本驗證", () => {
  it.each(["", "  ", "0", "12.30", "9999999999.99"])("接受 %s", (cost) => {
    expect(isValidCost(cost)).toBe(true)
  })
  it.each(["-1", "1.234", "10000000000", "NaN", "Infinity", "1e2"])("拒絕 %s", (cost) => {
    expect(isValidCost(cost)).toBe(false)
  })
})
