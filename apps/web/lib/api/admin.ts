import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type AdminUser = paths["/api/admin/users"]["get"]["responses"]["200"]["content"]["application/json"][number]

export async function listUsers(token: string | null): Promise<AdminUser[]> {
  return (await apiFetch("/admin/users", { accessToken: token })).json()
}

export async function setUserActive(userId: string, isActive: boolean, token: string | null): Promise<AdminUser> {
  return (await apiFetch(`/admin/users/${userId}`, {
    method: "PATCH",
    accessToken: token,
    body: JSON.stringify({ is_active: isActive }),
  })).json()
}

export async function sendTestNotification(userId: string, token: string | null): Promise<void> {
  await apiFetch(`/admin/users/${userId}/test-notification`, { method: "POST", accessToken: token })
}
