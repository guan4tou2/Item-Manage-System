import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type NotificationRead =
  paths["/api/notifications"]["get"]["responses"]["200"]["content"]["application/json"]["items"][number]

export type NotificationListResponse =
  paths["/api/notifications"]["get"]["responses"]["200"]["content"]["application/json"]

export type UnreadCountResponse =
  paths["/api/notifications/unread-count"]["get"]["responses"]["200"]["content"]["application/json"]

export async function listNotifications(
  params: { unreadOnly?: boolean; limit?: number; offset?: number },
  accessToken: string | null,
): Promise<NotificationListResponse> {
  const q = new URLSearchParams()
  if (params.unreadOnly) q.set("unread_only", "true")
  if (params.limit !== undefined) q.set("limit", String(params.limit))
  if (params.offset !== undefined) q.set("offset", String(params.offset))
  const res = await apiFetch(`/notifications${q.size ? `?${q}` : ""}`, { accessToken })
  return (await res.json()) as NotificationListResponse
}

export async function getUnreadCount(accessToken: string | null): Promise<UnreadCountResponse> {
  const res = await apiFetch("/notifications/unread-count", { accessToken })
  return (await res.json()) as UnreadCountResponse
}

export async function markNotificationRead(
  id: string,
  accessToken: string | null,
): Promise<NotificationRead> {
  const res = await apiFetch(`/notifications/${id}/read`, { method: "PATCH", accessToken })
  return (await res.json()) as NotificationRead
}

export async function markAllNotificationsRead(
  accessToken: string | null,
): Promise<{ marked: number }> {
  const res = await apiFetch("/notifications/mark-all-read", { method: "POST", accessToken })
  return (await res.json()) as { marked: number }
}

export async function deleteNotification(
  id: string,
  accessToken: string | null,
): Promise<void> {
  await apiFetch(`/notifications/${id}`, { method: "DELETE", accessToken })
}
