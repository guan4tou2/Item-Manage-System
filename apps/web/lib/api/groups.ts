import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type GroupSummary = paths["/api/groups"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type GroupDetail = paths["/api/groups/{group_id}"]["get"]["responses"]["200"]["content"]["application/json"]
export type GroupMember = GroupDetail["members"][number]
export type GroupCreateBody = paths["/api/groups"]["post"]["requestBody"]["content"]["application/json"]
export type GroupUpdateBody = paths["/api/groups/{group_id}"]["patch"]["requestBody"]["content"]["application/json"]

export async function listGroups(token: string | null): Promise<GroupSummary[]> {
  return (await apiFetch("/groups", { accessToken: token })).json()
}
export async function createGroup(body: GroupCreateBody, token: string | null): Promise<GroupSummary> {
  return (await apiFetch("/groups", { method: "POST", accessToken: token, body: JSON.stringify(body) })).json()
}
export async function getGroup(id: string, token: string | null): Promise<GroupDetail> {
  return (await apiFetch(`/groups/${id}`, { accessToken: token })).json()
}
export async function updateGroup(id: string, body: GroupUpdateBody, token: string | null): Promise<GroupSummary> {
  return (await apiFetch(`/groups/${id}`, { method: "PATCH", accessToken: token, body: JSON.stringify(body) })).json()
}
export async function deleteGroup(id: string, token: string | null): Promise<void> {
  await apiFetch(`/groups/${id}`, { method: "DELETE", accessToken: token })
}
export async function addGroupMember(groupId: string, username: string, token: string | null): Promise<GroupMember> {
  return (await apiFetch(`/groups/${groupId}/members`, { method: "POST", accessToken: token, body: JSON.stringify({ username }) })).json()
}
export async function removeGroupMember(groupId: string, userId: string, token: string | null): Promise<void> {
  await apiFetch(`/groups/${groupId}/members/${userId}`, { method: "DELETE", accessToken: token })
}
