import type { BatchRead } from "@/lib/api/batches"

type BatchValue = Pick<BatchRead, "quantity" | "unit_cost" | "is_depleted">

function cents(value: string | number | null | undefined): bigint {
  const [whole = "0", fraction = ""] = String(value ?? "0").split(".")
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0"))
}

/** D3：以整數分計算，未耗盡批次優先使用自身成本，再退回物品預設單價。 */
export function itemValuation(
  trackBatches: boolean,
  quantity: number,
  defaultCost: string | number | null | undefined,
  batches: readonly BatchValue[],
): string {
  const total = trackBatches
    ? batches.filter((batch) => !batch.is_depleted).reduce(
        (sum, batch) => sum + BigInt(batch.quantity) * cents(batch.unit_cost ?? defaultCost), 0n,
      )
    : BigInt(quantity) * cents(defaultCost)
  return `${total / 100n}.${String(total % 100n).padStart(2, "0")}`
}
