"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/categories"
import type { CategoryCreate, CategoryUpdate } from "@/lib/api/categories"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useCategories() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["categories"],
    queryFn: () => api.listCategories(token),
    enabled: token !== null,
  })
}

export function useCreateCategory() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CategoryCreate) => api.createCategory(body, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  })
}

export function useUpdateCategory() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: CategoryUpdate }) =>
      api.updateCategory(id, body, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["categories"] })
      qc.invalidateQueries({ queryKey: ["items"] })
    },
  })
}

export function useDeleteCategory() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.deleteCategory(id, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["categories"] })
      qc.invalidateQueries({ queryKey: ["items"] })
    },
  })
}
