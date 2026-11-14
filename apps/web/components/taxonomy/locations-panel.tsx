"use client"

import { Plus, Printer, Search } from "lucide-react"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { toast } from "sonner"

import { EditableOnly } from "@/components/common/editable-only"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { listItems } from "@/lib/api/items"
import { getApiErrorDetail } from "@/lib/api/client"
import { useAccessToken } from "@/lib/auth/use-auth"
import { useReadOnly } from "@/lib/auth/use-readonly"
import {
  useCreateLocation,
  useDeleteLocation,
  useLocationTree,
  useLocations,
  useMoveLocation,
  useUpdateLocation,
} from "@/lib/hooks/use-locations"
import { useBulkUpdateItems } from "@/lib/hooks/use-items"
import { useIsMobile } from "@/lib/hooks/use-is-mobile"
import {
  canMove,
  childrenOf,
  flattenList,
  flattenTree,
  searchNodes,
  type TreeFlatNode,
} from "@/lib/locations/tree"

import { LocationDeleteDialog } from "./location-delete-dialog"
import { LocationMoveSheet } from "./location-move-sheet"
import { TreeNodeRow } from "./location-tree-node"

function errorCode(error: unknown): string | undefined {
  const detail = getApiErrorDetail(error)
  if (detail) return detail
  const body = (error as { body?: { detail?: unknown } })?.body
  const inner = body?.detail
  if (inner && typeof inner === "object" && "code" in inner) {
    return String((inner as { code: unknown }).code)
  }
  return undefined
}

/** `/locations` 樹管理（§5.4／§5.7）：桌機拖放、行動 ⋯ 搬移、鍵盤操作、刪除限制。 */
export function LocationsPanel() {
  const t = useTranslations()
  const router = useRouter()
  const readOnly = useReadOnly()
  const token = useAccessToken()
  const isMobile = useIsMobile()
  const tree = useLocationTree()
  const flatList = useLocations()
  const create = useCreateLocation()
  const update = useUpdateLocation()
  const move = useMoveLocation()
  const remove = useDeleteLocation()
  const bulkUpdate = useBulkUpdateItems()

  const flat = useMemo<TreeFlatNode[]>(
    () =>
      tree.data && tree.data.length > 0
        ? flattenTree(tree.data)
        : flattenList(flatList.data ?? []),
    [tree.data, flatList.data],
  )

  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [focusedId, setFocusedId] = useState<number | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [draft, setDraft] = useState("")
  const [addingParent, setAddingParent] = useState<number | null>(null)
  const [addingChildOf, setAddingChildOf] = useState<number | null>(null)
  const [search, setSearch] = useState("")
  const [dragId, setDragId] = useState<number | null>(null)
  const [dropTargetId, setDropTargetId] = useState<number | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<TreeFlatNode | null>(null)
  const [moveTarget, setMoveTarget] = useState<TreeFlatNode | null>(null)
  const [announcement, setAnnouncement] = useState("")
  const containerRef = useRef<HTMLDivElement | null>(null)

  // 搜尋時自動展開命中節點的祖先
  useEffect(() => {
    if (!search.trim()) return
    const matches = searchNodes(flat, search)
    const ancestors = new Set<number>()
    const byId = new Map(flat.map((node) => [node.id, node]))
    for (const match of matches) {
      let current = byId.get(match.id)
      let guard = 0
      while (current?.parent_id !== null && current?.parent_id !== undefined && guard < 128) {
        ancestors.add(current.parent_id)
        current = byId.get(current.parent_id)
        guard += 1
      }
    }
    setExpanded((prev) => new Set([...prev, ...ancestors]))
  }, [search, flat])

  const visibleRows = useMemo(() => {
    const filtered = search.trim() ? searchNodes(flat, search) : flat
    const allowed = new Set(filtered.map((node) => node.id))
    const rows: Array<{ node: TreeFlatNode; depth: number }> = []
    const walk = (parentId: number | null, depth: number) => {
      for (const node of childrenOf(flat, parentId)) {
        if (!allowed.has(node.id)) continue
        rows.push({ node, depth })
        if (expanded.has(node.id)) walk(node.id, depth + 1)
      }
    }
    walk(null, 0)
    return rows
  }, [flat, search, expanded])

  const hasChildren = useCallback(
    (id: number) => childrenOf(flat, id).length > 0,
    [flat],
  )

  const toggle = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
    setFocusedId(id)
  }

  const startRename = (node: TreeFlatNode) => {
    setEditingId(node.id)
    setDraft(node.name)
  }

  const commitRename = async () => {
    if (editingId === null) return
    const node = flat.find((item) => item.id === editingId)
    const name = draft.trim()
    setEditingId(null)
    if (!node || !name || name === node.name) return
    try {
      await update.mutateAsync({ id: node.id, body: { name } })
      setAnnouncement(t("locations.tree.renamed", { name }))
    } catch (error) {
      if (errorCode(error) === "duplicate_name") {
        toast.error(t("locations.errors.duplicateName", { name }))
      } else {
        toast.error(t("locations.errors.renameFailed"))
      }
    }
  }

  const submitNew = async () => {
    const name = draft.trim()
    if (!name) return
    const parentId = addingChildOf ?? addingParent
    try {
      await create.mutateAsync({ name, parent_id: parentId, sort_order: 0 })
      if (parentId !== null) {
        setExpanded((prev) => new Set([...prev, parentId]))
      }
      setAnnouncement(t("locations.tree.created", { name }))
      setDraft("")
      setAddingChildOf(null)
    } catch (error) {
      if (errorCode(error) === "duplicate_name") {
        toast.error(t("locations.errors.duplicateName", { name }))
      } else {
        toast.error(t("locations.errors.createFailed"))
      }
    }
  }

  const performMove = async (nodeId: number, parentId: number | null) => {
    if (!canMove(flat, nodeId, parentId)) return
    const node = flat.find((item) => item.id === nodeId)
    const parentName =
      parentId === null
        ? t("locations.move.toRoot")
        : (flat.find((item) => item.id === parentId)?.path ?? "")
    setMoveTarget(null)
    try {
      await move.mutateAsync({ id: nodeId, parentId })
      setAnnouncement(t("locations.tree.moved", { name: node?.name ?? "", target: parentName }))
    } catch {
      toast.error(t("locations.errors.moveFailed"))
    }
  }

  const requestDelete = (node: TreeFlatNode) => {
    setDeleteTarget(node)
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    try {
      await remove.mutateAsync(deleteTarget.id)
      setAnnouncement(t("locations.tree.deleted", { name: deleteTarget.name }))
      setDeleteTarget(null)
    } catch (error) {
      const code = errorCode(error)
      if (code === "has_items" || code === "has_children") {
        // 伺服器仍擋下（前端計數可能過期）→ 保持對話框並提示
        toast.error(t("locations.errors.notEmpty"))
      } else {
        toast.error(t("locations.errors.deleteFailed"))
      }
    }
  }

  const moveItemsOfNode = async (targetId: number) => {
    if (!deleteTarget || !token) return
    try {
      const listed = await listItems(
        { locationId: deleteTarget.id, locationScope: "exact", perPage: 100 },
        token,
      )
      const ids = listed.items.map((item) => item.id)
      if (ids.length > 0) {
        await bulkUpdate.mutateAsync({
          item_ids: ids,
          location_id: targetId,
          tag_mode: "replace",
        })
      }
      toast.success(t("locations.delete.moved", { count: ids.length }))
      setDeleteTarget(null)
    } catch (error) {
      if (errorCode(error) === "invalid_location") {
        toast.error(t("locations.errors.moveFailed"))
      } else {
        toast.error(t("locations.errors.moveFailed"))
      }
    }
  }

  const onKeyDown = (event: React.KeyboardEvent) => {
    const index = visibleRows.findIndex((row) => row.node.id === focusedId)
    const current = index >= 0 ? visibleRows[index] : undefined
    if (event.key === "ArrowDown") {
      event.preventDefault()
      const next = visibleRows[Math.min(index + 1, visibleRows.length - 1)]
      if (next) setFocusedId(next.node.id)
      return
    }
    if (event.key === "ArrowUp") {
      event.preventDefault()
      const previous = visibleRows[Math.max(index - 1, 0)]
      if (previous) setFocusedId(previous.node.id)
      return
    }
    if (!current) return
    if (event.key === "ArrowRight") {
      event.preventDefault()
      if (hasChildren(current.node.id) && !expanded.has(current.node.id)) {
        toggle(current.node.id)
      } else {
        const child = childrenOf(flat, current.node.id)[0]
        if (child) setFocusedId(child.id)
      }
      return
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault()
      if (expanded.has(current.node.id)) {
        toggle(current.node.id)
      } else if (current.node.parent_id !== null) {
        setFocusedId(current.node.parent_id)
      }
      return
    }
    if (event.key === "F2") {
      if (readOnly) return
      event.preventDefault()
      startRename(current.node)
      return
    }
    if (event.key === "Enter") {
      event.preventDefault()
      if (hasChildren(current.node.id)) toggle(current.node.id)
    }
  }

  if (tree.isLoading) {
    return (
      <div className="space-y-2" data-testid="locations-tree-skeleton">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-5/6" />
        <Skeleton className="h-10 w-4/6" />
      </div>
    )
  }

  if (tree.isError) {
    return (
      <div className="space-y-2 rounded-sm border p-3 text-sm" role="alert">
        <p>{t("locations.tree.loadFailed")}</p>
        <Button type="button" size="sm" onClick={() => void tree.refetch()}>
          {t("scan.lookup.retry")}
        </Button>
      </div>
    )
  }

  const searchEmpty = search.trim().length > 0 && visibleRows.length === 0

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="relative min-w-56 flex-1">
          <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("locations.tree.searchPlaceholder")}
            aria-label={t("locations.tree.searchPlaceholder")}
            className="pl-8"
          />
        </div>
        <EditableOnly>
          <Button
            type="button"
            onClick={() => {
              setAddingParent(null)
              setAddingChildOf(null)
              setDraft("")
            }}
            disabled={create.isPending}
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("locations.tree.addRoot")}
          </Button>
        </EditableOnly>
        <Button
          type="button"
          variant="outline"
          onClick={() => router.push("/locations/labels")}
        >
          <Printer className="mr-2 h-4 w-4" />
          {t("locations.tree.printLabels")}
        </Button>
      </div>

      {!readOnly && addingChildOf === null && addingParent === null ? (
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Label htmlFor="new-location-name">{t("locations.tree.newRootLabel")}</Label>
            <Input
              id="new-location-name"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void submitNew()
                if (event.key === "Escape") setDraft("")
              }}
              placeholder={t("locations.tree.namePlaceholder")}
            />
          </div>
          <Button type="button" onClick={() => void submitNew()} disabled={create.isPending}>
            {t("taxonomy.locations.add")}
          </Button>
        </div>
      ) : null}

      {searchEmpty ? (
        <div className="space-y-2 rounded-sm border p-3 text-sm">
          <p>{t("locations.tree.noSearchResult")}</p>
          <EditableOnly>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={create.isPending}
              onClick={() => {
                setAddingParent(null)
                setAddingChildOf(null)
                setDraft(search)
                setSearch("")
                void create.mutateAsync({ name: search, parent_id: null, sort_order: 0 }).then(() => {
                  setAnnouncement(t("locations.tree.created", { name: search }))
                  setDraft("")
                })
              }}
            >
              {t("locations.tree.createFromSearch", { name: search })}
            </Button>
          </EditableOnly>
        </div>
      ) : null}

      {flat.length === 0 ? (
        <p className="text-muted-foreground">{t("taxonomy.locations.empty")}</p>
      ) : null}

      <div
        ref={containerRef}
        role="tree"
        aria-label={t("nav.locations")}
        className="rounded-sm border p-1"
        onKeyDown={onKeyDown}
        onDragOver={readOnly ? undefined : (event) => {
          if (dragId !== null && canMove(flat, dragId, null)) event.preventDefault()
        }}
        onDrop={readOnly ? undefined : (event) => {
          if (dragId !== null && canMove(flat, dragId, null)) {
            event.preventDefault()
            void performMove(dragId, null)
          }
          setDragId(null)
          setDropTargetId(null)
        }}
      >
        {visibleRows.map(({ node, depth }) => (
          <div key={node.id} style={{ paddingInlineStart: depth * 16 }}>
            <TreeNodeRow
              node={node}
              depth={depth}
              hasChildren={hasChildren(node.id)}
              expanded={expanded.has(node.id)}
              selected={focusedId === node.id}
              dragging={dragId === node.id}
              dropTarget={dropTargetId === node.id}
              dropInvalid={
                dragId !== null && dragId !== node.id && !canMove(flat, dragId, node.id)
              }
              isMobile={isMobile}
              readOnly={readOnly}
              editing={editingId === node.id}
              draft={draft}
              onToggle={() => toggle(node.id)}
              onFocusRow={() => setFocusedId(node.id)}
              onStartEdit={() => startRename(node)}
              onDraftChange={setDraft}
              onCommitEdit={() => void commitRename()}
              onCancelEdit={() => setEditingId(null)}
              onAddChild={() => {
                setAddingChildOf(node.id)
                setAddingParent(null)
                setDraft("")
              }}
              onDelete={() => requestDelete(node)}
              onMoveRequest={() => setMoveTarget(node)}
              onPrintLabel={() => router.push(`/locations/labels?ids=${node.id}`)}
              onDragStart={() => {
                setDragId(node.id)
                setFocusedId(node.id)
              }}
              onDragOver={(event) => {
                if (dragId === null) return
                if (!canMove(flat, dragId, node.id)) return
                event.preventDefault()
                setDropTargetId(node.id)
              }}
              onDrop={() => {
                if (dragId !== null) void performMove(dragId, node.id)
                setDragId(null)
                setDropTargetId(null)
              }}
              onDragEnd={() => {
                setDragId(null)
                setDropTargetId(null)
              }}
            />
            {!readOnly && addingChildOf === node.id ? (
              <div className="flex items-center gap-2 py-2" style={{ paddingInlineStart: (depth + 1) * 16 }}>
                <Input
                  autoFocus
                  value={draft}
                  aria-label={t("locations.tree.addChild")}
                  placeholder={t("locations.tree.namePlaceholder")}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void submitNew()
                    if (event.key === "Escape") {
                      setAddingChildOf(null)
                      setDraft("")
                    }
                  }}
                />
                <Button type="button" size="sm" onClick={() => void submitNew()} disabled={create.isPending}>
                  {t("taxonomy.locations.add")}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setAddingChildOf(null)
                    setDraft("")
                  }}
                >
                  {t("items.form.cancel")}
                </Button>
              </div>
            ) : null}
          </div>
        ))}
      </div>

      {!isMobile && !readOnly ? (
        <p className="text-xs text-muted-foreground">{t("locations.tree.dragHint")}</p>
      ) : null}

      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>

      <LocationDeleteDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        node={deleteTarget}
        itemCount={deleteTarget?.item_count ?? 0}
        childCount={
          deleteTarget
            ? flat.filter((node) => node.parent_id === deleteTarget.id).length
            : 0
        }
        onMoveItems={(targetId) => void moveItemsOfNode(targetId)}
        onFocusFirstChild={() => {
          if (!deleteTarget) return
          const child = childrenOf(flat, deleteTarget.id)[0]
          if (child) {
            setExpanded((prev) => new Set([...prev, deleteTarget.id]))
            setFocusedId(child.id)
          }
          setDeleteTarget(null)
        }}
        onDelete={() => void confirmDelete()}
        pending={remove.isPending}
        movingItems={bulkUpdate.isPending}
      />

      <LocationMoveSheet
        open={moveTarget !== null}
        onOpenChange={(open) => {
          if (!open) setMoveTarget(null)
        }}
        node={moveTarget}
        flat={flat}
        onConfirm={(parentId) => {
          if (moveTarget) void performMove(moveTarget.id, parentId)
        }}
        pending={move.isPending}
      />
    </div>
  )
}
