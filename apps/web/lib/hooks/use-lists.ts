"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/lists"
import type { EntryCreateBody, EntryUpdateBody, ListCreateBody, ListKind, ListUpdateBody } from "@/lib/api/lists"
import { useAccessToken } from "@/lib/auth/use-auth"

const STALE = 30_000

export function useLists(params: { kind?: ListKind } = {}) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["lists", "index", params],
    queryFn: () => api.listLists({ ...params, limit: 100 }, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useList(listId: string | null) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["lists", "detail", listId],
    queryFn: () => api.getList(listId as string, token),
    enabled: token !== null && listId !== null,
    staleTime: STALE,
  })
}

export function useCreateList() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ListCreateBody) => api.createList(body, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lists", "index"] }),
  })
}

export function useUpdateList(listId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ListUpdateBody) => api.updateList(listId, body, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lists", "index"] })
      qc.invalidateQueries({ queryKey: ["lists", "detail", listId] })
    },
  })
}

export function useDeleteList() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (listId: string) => api.deleteList(listId, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lists"] }),
  })
}

export function useCreateEntry(listId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: EntryCreateBody) => api.createEntry(listId, body, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lists", "detail", listId] })
      qc.invalidateQueries({ queryKey: ["lists", "index"] })
    },
  })
}

export function useUpdateEntry(listId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ entryId, body }: { entryId: string; body: EntryUpdateBody }) =>
      api.updateEntry(listId, entryId, body, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lists", "detail", listId] }),
  })
}

export function useToggleEntry(listId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (entryId: string) => api.toggleEntry(listId, entryId, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lists", "detail", listId] })
      qc.invalidateQueries({ queryKey: ["lists", "index"] })
    },
  })
}

export function useDeleteEntry(listId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (entryId: string) => api.deleteEntry(listId, entryId, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lists", "detail", listId] })
      qc.invalidateQueries({ queryKey: ["lists", "index"] })
    },
  })
}

export function useReorderEntries(listId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (entryIds: string[]) => api.reorderEntries(listId, entryIds, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lists", "detail", listId] }),
  })
}
