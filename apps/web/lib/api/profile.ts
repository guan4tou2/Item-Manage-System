import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type UserPublic = paths["/api/users/me"]["get"]["responses"]["200"]["content"]["application/json"]
export type UserProfileUpdate = paths["/api/users/me"]["patch"]["requestBody"]["content"]["application/json"]
export type PasswordChangeBody = paths["/api/users/me/change-password"]["post"]["requestBody"]["content"]["application/json"]

export async function getMe(token: string | null): Promise<UserPublic> {
  return (await apiFetch("/users/me", { accessToken: token })).json()
}

export async function updateProfile(body: UserProfileUpdate, token: string | null): Promise<UserPublic> {
  return (await apiFetch("/users/me", { method: "PATCH", accessToken: token, body: JSON.stringify(body) })).json()
}

export async function changePassword(body: PasswordChangeBody, token: string | null): Promise<void> {
  await apiFetch("/users/me/change-password", { method: "POST", accessToken: token, body: JSON.stringify(body) })
}

export async function bootstrapAdmin(token: string | null): Promise<UserPublic> {
  return (await apiFetch("/auth/bootstrap-admin", { method: "POST", accessToken: token })).json()
}
