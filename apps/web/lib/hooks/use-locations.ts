"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/locations"
import type { LocationCreate, LocationUpdate } from "@/lib/api/locations"
import { useAccessToken } from "@/lib/auth/use-auth"

function useInvalidateLocations() {
  const qc = useQueryClient()
  return () => {
    qc.invalidateQueries({ queryKey: ["locations"] })
    qc.invalidateQueries({ queryKey: ["items"] })
    qc.invalidateQueries({ queryKey: ["stats"] })
  }
}

/** 平坦清單（走訪序、含完整路徑）——供選擇器與行動版搜尋。 */
export function useLocations() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["locations"],
    queryFn: () => api.listLocations(token),
    enabled: token !== null,
  })
}

/** 巢狀樹（含直接物品數）——供 `/locations` 管理頁。 */
export function useLocationTree() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["locations", "tree"],
    queryFn: () => api.getLocationTree(token),
    enabled: token !== null,
  })
}

export function useCreateLocation() {
  const token = useAccessToken()
  const invalidate = useInvalidateLocations()
  return useMutation({
    mutationFn: (body: LocationCreate) => api.createLocation(body, token),
    onSuccess: invalidate,
  })
}

export function useUpdateLocation() {
  const token = useAccessToken()
  const invalidate = useInvalidateLocations()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: LocationUpdate }) =>
      api.updateLocation(id, body, token),
    onSuccess: invalidate,
  })
}

export function useMoveLocation() {
  const token = useAccessToken()
  const invalidate = useInvalidateLocations()
  return useMutation({
    mutationFn: ({ id, parentId }: { id: number; parentId: number | null }) =>
      api.moveLocation(id, parentId, token),
    onSuccess: invalidate,
  })
}

export function useReorderLocations() {
  const token = useAccessToken()
  const invalidate = useInvalidateLocations()
  return useMutation({
    mutationFn: (body: api.LocationReorder) => api.reorderLocations(body, token),
    onSuccess: invalidate,
  })
}

export function useDeleteLocation() {
  const token = useAccessToken()
  const invalidate = useInvalidateLocations()
  return useMutation({
    mutationFn: (id: number) => api.deleteLocation(id, token),
    onSuccess: invalidate,
  })
}

/** 平面圖與區域共用 PATCH；同步清單和樹，失敗還原完整快照。 */
export function useUpdateFloorPlan() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ["locations", "plan"],
    scope: { id: "location-plan" },
    mutationFn: ({ id, body }: { id: number; body: Pick<LocationUpdate, "plan_region" | "floor_plan_image_id"> }) =>
      api.updateLocation(id, body, token),
    onMutate: async ({ id, body }) => {
      await qc.cancelQueries({ queryKey: ["locations"] })
      const snapshot = qc.getQueriesData({ queryKey: ["locations"] })
      const patch = <T extends api.LocationRead>(rows: T[]): T[] => rows.map((row) => {
        const next = { ...row, ...(row.id === id ? body : {}) }
        if (row.parent_id === id && body.floor_plan_image_id === null) next.plan_region = null
        if ("children" in row) {
          return { ...next, children: patch((row as unknown as api.LocationTreeNode).children ?? []) }
        }
        return next
      })
      qc.setQueriesData<api.LocationRead[]>({ queryKey: ["locations"] }, (rows) => rows ? patch(rows) : rows)
      return { snapshot }
    },
    onError: (_error, _vars, context) => {
      for (const [key, data] of context?.snapshot ?? []) qc.setQueryData(key, data)
    },
    onSettled: () => {
      if (qc.isMutating({ mutationKey: ["locations", "plan"] }) === 1) {
        void qc.invalidateQueries({ queryKey: ["locations"] })
      }
    },
  })
}
