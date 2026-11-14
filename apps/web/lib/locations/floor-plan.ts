import type { LocationTreeNode, LocationUpdate } from "@/lib/api/locations"

export type PlanRegion = NonNullable<LocationUpdate["plan_region"]>
export type Point = { x: number; y: number }
const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v))
const round = (v: number) => Math.round(v * 10000) / 10000

export function toPixels(r: PlanRegion, width: number, height: number): PlanRegion {
  return { x: r.x * width, y: r.y * height, w: r.w * width, h: r.h * height }
}

export function toNormalized(r: PlanRegion, width: number, height: number): PlanRegion {
  return { x: r.x / width, y: r.y / height, w: r.w / width, h: r.h / height }
}

/** 反向拖曳也有效，最小矩形在邊緣向圖片內延伸。 */
export function dragRegion(start: Point, end: Point): PlanRegion {
  const x = clamp(Math.min(start.x, end.x), 0, 0.98)
  const y = clamp(Math.min(start.y, end.y), 0, 0.98)
  return {
    x: round(x),
    y: round(y),
    w: round(clamp(Math.max(start.x, end.x) - x, 0.02, 1 - x)),
    h: round(clamp(Math.max(start.y, end.y) - y, 0.02, 1 - y)),
  }
}

export function adjustRegion(r: PlanRegion, key: string, resize: boolean): PlanRegion | null {
  if (key === "Delete" || key === "Backspace") return null
  const dx = key === "ArrowRight" ? 0.01 : key === "ArrowLeft" ? -0.01 : 0
  const dy = key === "ArrowDown" ? 0.01 : key === "ArrowUp" ? -0.01 : 0
  return resize
    ? { ...r, w: round(clamp(r.w + dx, 0.02, 1 - r.x)), h: round(clamp(r.h + dy, 0.02, 1 - r.y)) }
    : { ...r, x: round(clamp(r.x + dx, 0, 1 - r.w)), y: round(clamp(r.y + dy, 0, 1 - r.h)) }
}

export function findPlanNode(nodes: LocationTreeNode[], id: number): LocationTreeNode | undefined {
  for (const node of nodes) {
    if (node.id === id) return node
    const found = findPlanNode(node.children ?? [], id)
    if (found) return found
  }
}

export function totalItems(node: LocationTreeNode): number {
  return (
    (node.item_count ?? 0) +
    (node.children ?? []).reduce((sum, child) => sum + totalItems(child), 0)
  )
}
