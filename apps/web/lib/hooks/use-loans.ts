"use client"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import * as api from "@/lib/api/loans"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useLoans(itemId: string) {
  const token = useAccessToken()
  return useQuery({ queryKey: ["loans", itemId], queryFn: () => api.listLoans(itemId, token), enabled: token !== null, staleTime: 30_000 })
}
export function useCreateLoan(itemId: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (body: api.LoanCreateBody) => api.createLoan(itemId, body, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["loans", itemId] }) })
}
export function useReturnLoan(itemId: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (loanId: string) => api.returnLoan(itemId, loanId, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["loans", itemId] }) })
}
export function useDeleteLoan(itemId: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (loanId: string) => api.deleteLoan(itemId, loanId, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["loans", itemId] }) })
}
