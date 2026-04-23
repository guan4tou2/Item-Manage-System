"use client"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import * as api from "@/lib/api/groups"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useGroups() {
  const token = useAccessToken()
  return useQuery({ queryKey: ["groups", "index"], queryFn: () => api.listGroups(token), enabled: token !== null, staleTime: 30_000 })
}
export function useGroup(id: string | null) {
  const token = useAccessToken()
  return useQuery({ queryKey: ["groups", "detail", id], queryFn: () => api.getGroup(id as string, token), enabled: token !== null && id !== null, staleTime: 30_000 })
}
export function useCreateGroup() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (body: api.GroupCreateBody) => api.createGroup(body, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) })
}
export function useUpdateGroup(id: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (body: api.GroupUpdateBody) => api.updateGroup(id, body, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) })
}
export function useDeleteGroup() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (id: string) => api.deleteGroup(id, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) })
}
export function useAddGroupMember(groupId: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (username: string) => api.addGroupMember(groupId, username, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) })
}
export function useRemoveGroupMember(groupId: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (userId: string) => api.removeGroupMember(groupId, userId, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) })
}
