import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type Transfer = paths["/api/transfers"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type TransferCreateBody = paths["/api/transfers"]["post"]["requestBody"]["content"]["application/json"]

export async function listTransfers(
  params: { direction?: "incoming" | "outgoing" | "both"; status_filter?: "pending" | "resolved" | "all" },
  token: string | null,
): Promise<Transfer[]> {
  const q = new URLSearchParams()
  if (params.direction) q.set("direction", params.direction)
  if (params.status_filter) q.set("status_filter", params.status_filter)
  return (await apiFetch(`/transfers${q.size ? `?${q}` : ""}`, { accessToken: token })).json()
}
export async function createTransfer(body: TransferCreateBody, token: string | null): Promise<Transfer> {
  return (await apiFetch("/transfers", { method: "POST", accessToken: token, body: JSON.stringify(body) })).json()
}
export async function acceptTransfer(id: string, token: string | null): Promise<Transfer> {
  return (await apiFetch(`/transfers/${id}/accept`, { method: "POST", accessToken: token })).json()
}
export async function rejectTransfer(id: string, token: string | null): Promise<Transfer> {
  return (await apiFetch(`/transfers/${id}/reject`, { method: "POST", accessToken: token })).json()
}
export async function cancelTransfer(id: string, token: string | null): Promise<Transfer> {
  return (await apiFetch(`/transfers/${id}/cancel`, { method: "POST", accessToken: token })).json()
}
