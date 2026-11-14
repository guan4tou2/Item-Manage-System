"use client"

import { useMemo } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { CategoryTreeNode } from "@/lib/api/categories"
import type { LocationRead } from "@/lib/api/locations"
import { usePendingItems } from "@/lib/offline/runtime"
import { optimisticItem } from "@/lib/offline/optimistic"
import * as api from "@/lib/api/items"
import type {
  ItemBulkDelete,
  ItemBulkUpdate,
  ItemCreate,
  ItemFilters,
  ItemUpdate,
} from "@/lib/api/items"
import { useAccessToken } from "@/lib/auth/use-auth"

function invalidateItemWorkflowSurfaces(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["items"] })
  qc.invalidateQueries({ queryKey: ["stats"] })
  qc.invalidateQueries({ queryKey: ["tags"] })
  qc.invalidateQueries({ queryKey: ["tags-with-counts"] })
  qc.invalidateQueries({ queryKey: ["locations"] })
  qc.invalidateQueries({ queryKey: ["categories"] })
}

export function useItems(filters: ItemFilters) {
  const token = useAccessToken()
  const pending = usePendingItems()
  const query = useQuery({
    queryKey: ["items", filters],
    queryFn: () => api.listItems(filters, token),
    enabled: token !== null,
  })
  const data = useMemo(() => {
    if (!query.data) return undefined
    const deleted = new Set(pending.filter((row) => row.kind === "delete").map((row) => row.item_id))
    return deleted.size ? { ...query.data, items: query.data.items.filter((item) => !deleted.has(item.id)) } : query.data
  }, [query.data, pending])
  return { ...query, data }
}

export function useItem(id: string | undefined) {
  const token = useAccessToken()
  const qc = useQueryClient()
  const pending = usePendingItems().find((row) => row.item_id === id && row.kind === "update" && row.status !== "conflict")
  const query = useQuery({
    queryKey: ["items", id],
    queryFn: () => api.getItem(id as string, token),
    enabled: token !== null && !!id,
  })
  const data = useMemo(() => query.data && pending ? optimisticItem({ ...query.data, track_batches: pending.trackBatches }, pending.values, qc.getQueryData<CategoryTreeNode[]>(["categories"]), qc.getQueryData<LocationRead[]>(["locations"])) : query.data, [query.data, pending, qc])
  return { ...query, data }
}

export function useCreateItem(idempotencyKey?: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ItemCreate) => api.createItem(body, token, idempotencyKey),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["items"] })
      qc.invalidateQueries({ queryKey: ["tags"] })
    },
  })
}

export function useUpdateItem(id: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ItemUpdate) => api.updateItem(id, body, token),
    onSuccess: (data) => {
      qc.setQueryData(["items", id], data)
      qc.invalidateQueries({ queryKey: ["items"] })
      qc.invalidateQueries({ queryKey: ["tags"] })
    },
  })
}

export function useDeleteItem() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteItem(id, token),
    onSuccess: (_data, id) => {
      qc.removeQueries({ queryKey: ["items", id] })
      qc.invalidateQueries({ queryKey: ["items"] })
    },
  })
}

export function useBulkUpdateItems() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ItemBulkUpdate) => api.bulkUpdateItems(body, token),
    onSuccess: () => invalidateItemWorkflowSurfaces(qc),
  })
}

export function useBulkDeleteItems() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ItemBulkDelete) => api.bulkDeleteItems(body, token),
    onSuccess: () => invalidateItemWorkflowSurfaces(qc),
  })
}
