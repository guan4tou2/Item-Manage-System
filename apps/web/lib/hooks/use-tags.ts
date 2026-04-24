"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/tags"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useTags(q: string | undefined = undefined) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["tags", q ?? ""],
    queryFn: () => api.listTags(q, token),
    enabled: token !== null,
  })
}

/**
 * Invalidate every query that shows tags so a tag mutation is
 * reflected everywhere the user might be looking.
 */
function invalidateAllTagSurfaces(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["tags"] })
  qc.invalidateQueries({ queryKey: ["tags-with-counts"] })
  // items carry tag arrays; rename/merge/delete all change that
  qc.invalidateQueries({ queryKey: ["items"] })
  qc.invalidateQueries({ queryKey: ["stats", "by-tag"] })
}

export function useTagsWithCounts() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["tags-with-counts"],
    queryFn: () => api.listTagsWithCounts(token),
    enabled: token !== null,
  })
}

export function useRenameTag() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tagId, name }: { tagId: number; name: string }) =>
      api.renameTag(tagId, name, token),
    onSuccess: () => invalidateAllTagSurfaces(qc),
  })
}

export function useMergeTag() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sourceId, targetId }: { sourceId: number; targetId: number }) =>
      api.mergeTag(sourceId, targetId, token),
    onSuccess: () => invalidateAllTagSurfaces(qc),
  })
}

export function useDeleteTag() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tagId, force }: { tagId: number; force: boolean }) =>
      api.deleteTag(tagId, force, token),
    onSuccess: () => invalidateAllTagSurfaces(qc),
  })
}

export function usePruneOrphanTags() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.pruneOrphanTags(token),
    onSuccess: () => invalidateAllTagSurfaces(qc),
  })
}
