import { apiFetch } from "./client"

export interface ApiTokenRead {
  id: string
  name: string
  last_used_at: string | null
  created_at: string
}

export interface ApiTokenCreated extends ApiTokenRead {
  token: string
}

export async function listTokens(token: string | null): Promise<ApiTokenRead[]> {
  return (await apiFetch("/users/me/tokens", { accessToken: token })).json()
}

export async function createToken(name: string, token: string | null): Promise<ApiTokenCreated> {
  return (await apiFetch("/users/me/tokens", {
    method: "POST",
    accessToken: token,
    body: JSON.stringify({ name }),
  })).json()
}

export async function deleteToken(id: string, token: string | null): Promise<void> {
  await apiFetch(`/users/me/tokens/${id}`, { method: "DELETE", accessToken: token })
}
