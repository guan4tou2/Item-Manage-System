"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/locations"
import type { LocationCreate, LocationUpdate } from "@/lib/api/locations"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useLocations() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["locations"],
    queryFn: () => api.listLocations(token),
    enabled: token !== null,
  })
}

export function useCreateLocation() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: LocationCreate) => api.createLocation(body, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["locations"] }),
  })
}

export function useUpdateLocation() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: LocationUpdate }) =>
      api.updateLocation(id, body, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["locations"] })
      qc.invalidateQueries({ queryKey: ["items"] })
    },
  })
}

export function useDeleteLocation() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.deleteLocation(id, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["locations"] })
      qc.invalidateQueries({ queryKey: ["items"] })
    },
  })
}
