import type { LocationRead, LocationTreeNode } from "@/lib/api/locations"

/** 樹工具（純函式）——拖放合法性、行動版扁平搜尋、cascading 選擇器共用。 */

export interface TreeFlatNode {
  id: number
  parent_id: number | null
  name: string
  kind: string | null
  sort_order: number
  path: string
  item_count: number
  floor_plan_image_id?: string | null
}

export function flattenTree(nodes: LocationTreeNode[]): TreeFlatNode[] {
  const out: TreeFlatNode[] = []
  const visit = (node: LocationTreeNode) => {
    out.push({
      id: node.id,
      parent_id: node.parent_id ?? null,
      name: node.name,
      kind: node.kind ?? null,
      sort_order: node.sort_order,
      path: node.path,
      item_count: node.item_count ?? 0,
      floor_plan_image_id: node.floor_plan_image_id,
    })
    for (const child of node.children ?? []) visit(child)
  }
  for (const root of nodes) visit(root)
  return out
}

/** 由平坦清單（`GET /api/locations`）建立同一結構。 */
export function flattenList(nodes: LocationRead[]): TreeFlatNode[] {
  return nodes.map((node) => ({
    id: node.id,
    parent_id: node.parent_id ?? null,
    name: node.name,
    kind: node.kind ?? null,
    sort_order: node.sort_order,
    path: node.path,
    item_count: 0,
    floor_plan_image_id: node.floor_plan_image_id,
  }))
}

export function childrenOf(
  flat: TreeFlatNode[],
  parentId: number | null,
): TreeFlatNode[] {
  return flat
    .filter((node) => node.parent_id === parentId)
    .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))
}

/** `candidateId` 是否為 `ancestorId` 的子孫（含自身 → false）。 */
export function isDescendant(
  flat: TreeFlatNode[],
  ancestorId: number,
  candidateId: number,
): boolean {
  const byId = new Map(flat.map((node) => [node.id, node]))
  let current = byId.get(candidateId)
  let guard = 0
  while (current && current.parent_id !== null && guard < 128) {
    if (current.parent_id === ancestorId) return true
    current = byId.get(current.parent_id)
    guard += 1
  }
  return false
}

/** 拖放合法性：不能放到自己或自己的子孫之下（`targetId = null` → 移到最上層）。 */
export function canMove(
  flat: TreeFlatNode[],
  dragId: number,
  targetId: number | null,
): boolean {
  if (targetId === null) {
    const node = flat.find((item) => item.id === dragId)
    return node !== undefined && node.parent_id !== null
  }
  if (targetId === dragId) return false
  if (isDescendant(flat, dragId, targetId)) return false
  const node = flat.find((item) => item.id === dragId)
  return node !== undefined && node.parent_id !== targetId
}

export function searchNodes(flat: TreeFlatNode[], query: string): TreeFlatNode[] {
  const needle = query.trim().toLowerCase()
  if (!needle) return flat
  return flat.filter(
    (node) =>
      node.name.toLowerCase().includes(needle) ||
      node.path.toLowerCase().includes(needle),
  )
}

/** 節點至 root 的祖先 id 鏈（不含自身）——供 cascading 選擇器還原。 */
export function ancestorChain(flat: TreeFlatNode[], id: number): number[] {
  const byId = new Map(flat.map((node) => [node.id, node]))
  const chain: number[] = []
  let current = byId.get(id)
  let guard = 0
  while (current && current.parent_id !== null && guard < 128) {
    chain.unshift(current.parent_id)
    current = byId.get(current.parent_id)
    guard += 1
  }
  return chain
}

/** 顯示用：超過 `max` 層時中間截斷（「1F / … / 抽屜」）。 */
export function truncatePath(path: string, max = 3): string {
  const parts = path.split(" / ")
  if (parts.length <= max) return path
  return [parts[0], "…", ...parts.slice(-(max - 2))].join(" / ")
}
