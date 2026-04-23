import { apiFetch } from "./client"

export async function toggleFavorite(itemId: string, accessToken: string | null): Promise<void> {
  await apiFetch(`/items/${itemId}/favorite`, { method: "POST", accessToken })
}
