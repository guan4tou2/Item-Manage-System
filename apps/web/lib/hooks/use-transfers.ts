"use client"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import * as api from "@/lib/api/transfers"
import { useAccessToken } from "@/lib/auth/use-auth"

type ListParams = { direction?: "incoming" | "outgoing" | "both"; status_filter?: "pending" | "resolved" | "all" }

export function useTransfers(params: ListParams = {}) {
  const token = useAccessToken()
  return useQuery({ queryKey: ["transfers", "index", params], queryFn: () => api.listTransfers(params, token), enabled: token !== null, staleTime: 30_000 })
}
function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["transfers"] })
  qc.invalidateQueries({ queryKey: ["items"] })
  qc.invalidateQueries({ queryKey: ["notifications"] })
}
export function useCreateTransfer() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (body: api.TransferCreateBody) => api.createTransfer(body, token), onSuccess: () => invalidateAll(qc) })
}
export function useAcceptTransfer() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (id: string) => api.acceptTransfer(id, token), onSuccess: () => invalidateAll(qc) })
}
export function useRejectTransfer() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (id: string) => api.rejectTransfer(id, token), onSuccess: () => invalidateAll(qc) })
}
export function useCancelTransfer() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (id: string) => api.cancelTransfer(id, token), onSuccess: () => invalidateAll(qc) })
}
