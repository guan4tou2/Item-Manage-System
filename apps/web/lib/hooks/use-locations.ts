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
