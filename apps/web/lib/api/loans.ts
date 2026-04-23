import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type Loan = paths["/api/items/{item_id}/loans"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type LoanCreateBody = paths["/api/items/{item_id}/loans"]["post"]["requestBody"]["content"]["application/json"]

export async function listLoans(itemId: string, token: string | null): Promise<Loan[]> {
  return (await apiFetch(`/items/${itemId}/loans`, { accessToken: token })).json()
}
export async function createLoan(itemId: string, body: LoanCreateBody, token: string | null): Promise<Loan> {
  return (await apiFetch(`/items/${itemId}/loans`, { method: "POST", accessToken: token, body: JSON.stringify(body) })).json()
}
export async function returnLoan(itemId: string, loanId: string, token: string | null): Promise<Loan> {
  return (await apiFetch(`/items/${itemId}/loans/${loanId}/return`, { method: "POST", accessToken: token })).json()
}
export async function deleteLoan(itemId: string, loanId: string, token: string | null): Promise<void> {
  await apiFetch(`/items/${itemId}/loans/${loanId}`, { method: "DELETE", accessToken: token })
}
