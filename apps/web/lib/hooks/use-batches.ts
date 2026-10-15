"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/batches"
import type { BatchCreate, BatchRead, BatchUpdate } from "@/lib/api/batches"
import type { ItemRead } from "@/lib/api/items"
import { useAccessToken } from "@/lib/auth/use-auth"

function invalidateBatchSurfaces(qc: ReturnType<typeof useQueryClient>) {
  // ["batches"] 前綴同時涵蓋 ["batches", itemId]；["items"] 前綴涵蓋 ["items", id] 詳情
  qc.invalidateQueries({ queryKey: ["batches"] })
  qc.invalidateQueries({ queryKey: ["items"] })
  qc.invalidateQueries({ queryKey: ["stats"] })
}

export function useBatches(itemId: string | undefined) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["batches", itemId],
    queryFn: () => api.listBatches(itemId as string, token),
    enabled: token !== null && !!itemId,
  })
}

export function useCreateBatch(itemId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: BatchCreate) => api.createBatch(itemId, body, token),
    onSuccess: () => invalidateBatchSurfaces(qc),
  })
}

export function useUpdateBatch(itemId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ batchId, body }: { batchId: string; body: BatchUpdate }) =>
      api.updateBatch(itemId, batchId, body, token),
    onSuccess: () => invalidateBatchSurfaces(qc),
  })
}

export function useDeleteBatch(itemId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (batchId: string) => api.deleteBatch(itemId, batchId, token),
    onSuccess: () => invalidateBatchSurfaces(qc),
  })
}

export function useConsumeBatch(itemId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ batchId, quantity }: { batchId: string; quantity: number }) =>
      api.consumeBatch(itemId, batchId, { quantity }, token),
    onMutate: async ({ batchId, quantity }) => {
      await qc.cancelQueries({ queryKey: ["batches", itemId] })
      const previousBatches = qc.getQueryData<BatchRead[]>(["batches", itemId])
      const previousItem = qc.getQueryData<ItemRead>(["items", itemId])
      if (previousBatches) {
        qc.setQueryData<BatchRead[]>(
          ["batches", itemId],
          previousBatches.map((batch) =>
            batch.id === batchId
              ? {
                  ...batch,
                  quantity: Math.max(0, batch.quantity - quantity),
                  is_depleted: batch.quantity - quantity <= 0,
                }
              : batch,
          ),
        )
      }
      if (previousItem) {
        qc.setQueryData<ItemRead>(["items", itemId], {
          ...previousItem,
          quantity: Math.max(0, previousItem.quantity - quantity),
        })
      }
      return { previousBatches, previousItem }
    },
    onError: (_error, _variables, context) => {
      if (context?.previousBatches !== undefined) {
        qc.setQueryData(["batches", itemId], context.previousBatches)
      }
      if (context?.previousItem !== undefined) {
        qc.setQueryData(["items", itemId], context.previousItem)
      }
    },
    onSettled: () => invalidateBatchSurfaces(qc),
  })
}

export function useConsumeFefo(itemId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (quantity: number) => api.consumeFefo(itemId, { quantity }, token),
    onSuccess: () => invalidateBatchSurfaces(qc),
  })
}

export function useDisableBatches(itemId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.disableBatches(itemId, token),
    onSuccess: () => invalidateBatchSurfaces(qc),
  })
}
