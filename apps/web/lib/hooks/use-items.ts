"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/items"
import type { ItemCreate, ItemFilters, ItemUpdate } from "@/lib/api/items"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useItems(filters: ItemFilters) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["items", filters],
    queryFn: () => api.listItems(filters, token),
    enabled: token !== null,
  })
}

export function useItem(id: string | undefined) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["items", id],
    queryFn: () => api.getItem(id as string, token),
    enabled: token !== null && !!id,
  })
}

export function useCreateItem() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ItemCreate) => api.createItem(body, token),
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["items"] }),
  })
}
