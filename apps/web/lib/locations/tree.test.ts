import { describe, expect, it } from "vitest"

import type { LocationTreeNode } from "@/lib/api/locations"

import {
  ancestorChain,
  canMove,
  childrenOf,
  flattenTree,
  isDescendant,
  searchNodes,
  truncatePath,
} from "./tree"

function node(
  id: number,
  name: string,
  parent_id: number | null,
  children: LocationTreeNode[] = [],
  sort_order = 0,
  item_count = 0,
): LocationTreeNode {
  return {
    id,
    parent_id,
    name,
    kind: null,
    sort_order,
    floor_plan_image_id: null,
    path: "",
    item_count,
    children,
  } as LocationTreeNode
}

const tree: LocationTreeNode[] = [
  node(1, "1F", null, [
    node(2, "廚房", 1, [node(4, "上櫃", 2), node(5, "冰箱", 2, [], 1)], 0, 2),
    node(3, "客廳", 1),
  ], 0, 1),
  node(6, "2F", null, [node(7, "書房", 6)], 1),
]

const flat = flattenTree(tree)

describe("flattenTree / childrenOf", () => {
  it("flattens the tree depth-first with parent ids", () => {
    expect(flat.map((n) => n.id)).toEqual([1, 2, 4, 5, 3, 6, 7])
    expect(flat.find((n) => n.id === 4)?.parent_id).toBe(2)
    expect(flat.find((n) => n.id === 4)?.item_count).toBe(0)
  })

  it("lists children sorted by sort_order then name", () => {
    expect(childrenOf(flat, 2).map((n) => n.name)).toEqual(["上櫃", "冰箱"])
    expect(childrenOf(flat, null).map((n) => n.name)).toEqual(["1F", "2F"])
  })
})

describe("isDescendant / canMove", () => {
  it("detects descendants", () => {
    expect(isDescendant(flat, 1, 4)).toBe(true)
    expect(isDescendant(flat, 2, 4)).toBe(true)
    expect(isDescendant(flat, 4, 1)).toBe(false)
    expect(isDescendant(flat, 2, 2)).toBe(false)
  })

  it("rejects dropping onto self or a descendant", () => {
    expect(canMove(flat, 2, 2)).toBe(false)
    expect(canMove(flat, 1, 4)).toBe(false)
    expect(canMove(flat, 2, 6)).toBe(true)
    expect(canMove(flat, 4, 3)).toBe(true)
  })

  it("allows dropping to root only when not already a root", () => {
    expect(canMove(flat, 4, null)).toBe(true)
    expect(canMove(flat, 1, null)).toBe(false)
  })

  it("rejects dropping onto the current parent (no-op)", () => {
    expect(canMove(flat, 4, 2)).toBe(false)
    expect(canMove(flat, 6, null)).toBe(false)
  })
})

describe("searchNodes / ancestorChain / truncatePath", () => {
  it("searches by name or path, case-insensitive", () => {
    expect(searchNodes(flat, "上櫃").map((n) => n.id)).toEqual([4])
    expect(searchNodes(flat, "").length).toBe(flat.length)
    expect(searchNodes(flat, "廚房").map((n) => n.id)).toEqual([2])
  })

  it("builds the ancestor chain", () => {
    expect(ancestorChain(flat, 4)).toEqual([1, 2])
    expect(ancestorChain(flat, 1)).toEqual([])
  })

  it("truncates long paths in the middle", () => {
    expect(truncatePath("1F / 廚房 / 上櫃")).toBe("1F / 廚房 / 上櫃")
    expect(truncatePath("1F / 廚房 / 上櫃 / 抽屜")).toBe("1F / … / 抽屜")
  })
})
